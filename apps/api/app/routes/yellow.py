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
