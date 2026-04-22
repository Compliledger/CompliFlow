from fastapi import APIRouter, HTTPException
from app.models.yellow import (
    SessionPreflightRequest,
    SessionPreflightResponse,
    OrderSubmitRequest,
    OrderSubmitResponse,
    OrderStatusResponse,
)

router = APIRouter()

_orders: dict = {}
_order_counter = 0


@router.post("/session/preflight", response_model=SessionPreflightResponse)
def session_preflight(request: SessionPreflightRequest):
    return SessionPreflightResponse(
        valid=True,
        expires_at=1700000000,
        allowance_remaining=1000,
    )


@router.post("/order/submit", response_model=OrderSubmitResponse)
def order_submit(request: OrderSubmitRequest):
    global _order_counter
    _order_counter += 1
    order_id = f"order_{_order_counter}"
    _orders[order_id] = {"status": "SUBMITTED", "details": {}}
    return OrderSubmitResponse(order_id=order_id, status="SUBMITTED")


@router.get("/order/{order_id}/status", response_model=OrderStatusResponse)
def order_status(order_id: str):
    order = _orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderStatusResponse(status=order["status"], details=order["details"])
from pydantic import BaseModel
from app.services.yellow_client import yellow_client
from app.services.session_service import SessionService
from app.services.audit_service import AuditService
from app.services.proof.receipt_signer import ReceiptSigner
import uuid

router = APIRouter()


class SessionPreflightRequest(BaseModel):
    session_key: str
    wallet: str


class OrderSubmitRequest(BaseModel):
    intent: dict
    receipt: dict


@router.post("/session/preflight")
async def session_preflight(body: SessionPreflightRequest):
    is_valid, reason = SessionService.validate_session(
        session_key=body.session_key,
        wallet=body.wallet,
    )

    if not is_valid:
        return {
            "valid": False,
            "error": reason,
            "message": "Session validation failed",
        }

    yellow_result = await yellow_client.validate_session(body.session_key, body.wallet)
    yellow_available = yellow_result.get("mode") != "error" and yellow_result.get("valid", False)

    return {
        "valid": True,
        "session_key": body.session_key,
        "wallet": body.wallet,
        "expires_at": yellow_result.get("expires_at") if yellow_available else None,
        "allowance_remaining": yellow_result.get("allowance_remaining") if yellow_available else None,
        "yellow_status": "available" if yellow_available else "unavailable",
    }


@router.post("/order/submit")
async def order_submit(body: OrderSubmitRequest):
    intent = body.intent
    receipt = body.receipt

    # Proof bundle is required; if present it must verify before we touch
    # any session state or downstream venue.
    proof_bundle = receipt.get("proof_bundle") if isinstance(receipt, dict) else None
    if not proof_bundle:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "proof_missing",
                "reason": "Receipt is missing a proof_bundle",
            },
        )

    proof_ok, proof_reason = ReceiptSigner.verify_bundle(proof_bundle)
    if not proof_ok:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "proof_invalid",
                "reason": proof_reason,
            },
        )

    session_key = intent.get("session_key")
    wallet = intent.get("user_wallet") or intent.get("wallet")
    amount = intent.get("amount", 0)
    price = intent.get("price", 1)
    
    is_valid, reason = SessionService.validate_session(
        session_key=session_key,
        wallet=wallet,
        required_allowance=amount * price
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Session validation failed",
                "reason": reason
            }
        )
    
    success, consume_reason = SessionService.consume_allowance(
        session_key=session_key,
        wallet=wallet,
        amount=amount * price
    )
    
    if not success:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Failed to consume allowance",
                "reason": consume_reason
            }
        )
    
    order_data = {
        "intent": body.intent,
        "receipt": body.receipt
    }
    
    result = await yellow_client.submit_order(order_data)
    
    if result.get("error"):
        raise HTTPException(
            status_code=500,
            detail={
                "error": result.get("error"),
                "message": result.get("message", "Failed to submit order")
            }
        )
    
    order_id = result.get("order_id", result.get("id"))
    yellow_order_id = result.get("order_id")
    
    AuditService.log_order_submission(
        order_id=order_id,
        session_key=session_key,
        wallet=wallet,
        yellow_order_id=yellow_order_id
    )
    
    AuditService.log_order_status_change(
        order_id=order_id,
        old_status="RECEIPT_SIGNED",
        new_status="ORDER_SUBMITTED",
        details=result
    )
    
    return {
        "order_id": order_id,
        "status": result.get("status", "SUBMITTED"),
        "details": result
    }


@router.get("/order/{order_id}/status")
async def order_status(order_id: str):
    result = await yellow_client.get_order_status(order_id)
    
    if result.get("error"):
        AuditService.log_event(
            event_type="ORDER_STATUS_QUERY",
            status="ERROR",
            order_id=order_id,
            details={"error": result.get("error")}
        )
        return {
            "status": "UNKNOWN",
            "error": result.get("error"),
            "message": result.get("message", "Failed to fetch order status")
        }
    
    current_status = result.get("status", "SUBMITTED")
    
    AuditService.log_event(
        event_type="ORDER_STATUS_QUERY",
        status=current_status,
        order_id=order_id,
        details=result
    )
    
    return {
        "status": current_status,
        "details": result
    }


@router.get("/health")
async def yellow_health():
    result = await yellow_client.health_check()
    return result


@router.get("/market/data")
async def market_data(asset_pair: str = None):
    result = await yellow_client.get_market_data(asset_pair)
    
    if result.get("error"):
        raise HTTPException(
            status_code=500,
            detail={
                "error": result.get("error"),
                "message": result.get("message", "Failed to fetch market data")
            }
        )
    
    return result
