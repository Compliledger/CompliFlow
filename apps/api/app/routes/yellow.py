from fastapi import APIRouter
from pydantic import BaseModel
import uuid

router = APIRouter()

# In-memory order store
_orders: dict[str, dict] = {}


class SessionPreflightRequest(BaseModel):
    session_key: str
    wallet: str


class OrderSubmitRequest(BaseModel):
    intent: dict
    receipt: dict


@router.post("/session/preflight")
def session_preflight(body: SessionPreflightRequest):
    return {
        "valid": True,
        "expires_at": 1700000000,
        "allowance_remaining": 1000,
    }


@router.post("/order/submit")
def order_submit(body: OrderSubmitRequest):
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    _orders[order_id] = {"status": "SUBMITTED", "details": {}}
    return {"order_id": order_id, "status": "SUBMITTED"}


@router.get("/order/{order_id}/status")
def order_status(order_id: str):
    order = _orders.get(order_id, {"status": "SUBMITTED", "details": {}})
    return {"status": order["status"], "details": order["details"]}
