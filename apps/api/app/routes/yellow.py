from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.yellow_client import yellow_client

router = APIRouter()


class SessionPreflightRequest(BaseModel):
    session_key: str
    wallet: str


class OrderSubmitRequest(BaseModel):
    intent: dict
    receipt: dict


@router.post("/session/preflight")
async def session_preflight(body: SessionPreflightRequest):
    result = await yellow_client.validate_session(body.session_key, body.wallet)
    
    if result.get("error"):
        return {
            "valid": False,
            "error": result.get("error"),
            "message": result.get("message", "Session validation failed")
        }
    
    return {
        "valid": result.get("valid", True),
        "expires_at": result.get("expires_at", 1700000000),
        "allowance_remaining": result.get("allowance_remaining", 1000),
    }


@router.post("/order/submit")
async def order_submit(body: OrderSubmitRequest):
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
    
    return {
        "order_id": result.get("order_id", result.get("id")),
        "status": result.get("status", "SUBMITTED"),
        "details": result
    }


@router.get("/order/{order_id}/status")
async def order_status(order_id: str):
    result = await yellow_client.get_order_status(order_id)
    
    if result.get("error"):
        return {
            "status": "UNKNOWN",
            "error": result.get("error"),
            "message": result.get("message", "Failed to fetch order status")
        }
    
    return {
        "status": result.get("status", "SUBMITTED"),
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
