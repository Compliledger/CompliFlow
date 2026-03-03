import threading

from fastapi import APIRouter, HTTPException

router = APIRouter()

_orders: dict[int, dict] = {}
_order_counter: int = 0
_lock = threading.Lock()


@router.post("/submit")
def order_submit(order: dict):
    global _order_counter
    with _lock:
        _order_counter += 1
        order_id = _order_counter
        _orders[order_id] = order
    return {"order_id": order_id}


@router.get("/{order_id}")
def order_get(order_id: int):
    with _lock:
        order = _orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order_id, "order": order}
