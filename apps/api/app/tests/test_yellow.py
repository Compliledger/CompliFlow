import threading

from fastapi.testclient import TestClient

from app.main import app
import app.routes.yellow as yellow_module

client = TestClient(app)


def _reset_state():
    with yellow_module._lock:
        yellow_module._orders.clear()
        yellow_module._order_counter = 0


def test_order_submit_returns_order_id():
    _reset_state()
    r = client.post("/v1/orders/submit", json={"item": "widget", "qty": 1})
    assert r.status_code == 200
    assert r.json()["order_id"] == 1


def test_order_get_returns_order():
    _reset_state()
    client.post("/v1/orders/submit", json={"item": "widget", "qty": 1})
    r = client.get("/v1/orders/1")
    assert r.status_code == 200
    assert r.json()["order"]["item"] == "widget"


def test_order_get_not_found():
    _reset_state()
    r = client.get("/v1/orders/9999")
    assert r.status_code == 404


def test_concurrent_orders_have_unique_ids():
    """Concurrent submissions must produce unique order IDs with no overwrites."""
    _reset_state()

    results = []
    errors = []

    def submit():
        try:
            r = client.post("/v1/orders/submit", json={"item": "concurrent"})
            results.append(r.json()["order_id"])
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=submit) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Unexpected errors: {errors}"
    assert len(results) == 50, f"Expected 50 results, got {len(results)}"
    assert len(set(results)) == 50, "Duplicate order IDs detected – race condition present"

    with yellow_module._lock:
        assert len(yellow_module._orders) == 50, "Orders were silently overwritten"
