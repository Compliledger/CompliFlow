"""Tests for the Yellow order submission route.

Covers:
  * the route refuses to forward an order with a missing or invalid proof
    bundle,
  * the order lifecycle progresses correctly through the recognised
    statuses (SUBMITTED → MATCHED → ESCROW_LOCKED → SETTLED).
"""

from __future__ import annotations

import base64


def _submit(client, intent, receipt):
    return client.post(
        "/v1/yellow/order/submit",
        json={"intent": intent, "receipt": receipt},
    )


# ---------------------------------------------------------------------------
# Proof enforcement on submit
# ---------------------------------------------------------------------------

def test_submit_rejects_missing_proof_bundle(client, test_intent, fake_yellow):
    """No proof_bundle on the receipt → 400, never forwarded to Yellow."""
    response = _submit(client, test_intent, receipt={"signature": "abc", "payload": {}})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "proof_missing"
    assert fake_yellow.submitted_orders == []


def test_submit_rejects_tampered_proof_bundle(
    client, test_intent, make_proof_bundle, fake_yellow
):
    """A bundle whose decision has been mutated must not be accepted."""
    bundle = make_proof_bundle(test_intent)
    bundle["decision"] = {**bundle["decision"], "reason_codes": ["INJECTED"]}

    response = _submit(client, test_intent, receipt={"proof_bundle": bundle})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "proof_invalid"
    assert detail["reason"] == "proof_hash_mismatch"
    assert fake_yellow.submitted_orders == []


def test_submit_rejects_invalid_signature(
    client, test_intent, make_proof_bundle, fake_yellow
):
    bundle = make_proof_bundle(test_intent)
    bundle["signature"] = base64.b64encode(b"\x00" * 64).decode()

    response = _submit(client, test_intent, receipt={"proof_bundle": bundle})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "proof_invalid"
    assert response.json()["detail"]["reason"] == "invalid_signature"
    assert fake_yellow.submitted_orders == []


def test_submit_rejects_expired_proof_bundle(
    client, test_intent, make_proof_bundle, fake_yellow
):
    bundle = make_proof_bundle(test_intent, ttl_seconds=-10)

    response = _submit(client, test_intent, receipt={"proof_bundle": bundle})

    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "expired"


# ---------------------------------------------------------------------------
# Lifecycle progression
# ---------------------------------------------------------------------------

def test_submit_with_valid_proof_returns_order_id(
    client, test_intent, make_proof_bundle, fake_yellow
):
    bundle = make_proof_bundle(test_intent)
    response = _submit(client, test_intent, receipt={"proof_bundle": bundle})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUBMITTED"
    assert data["order_id"]
    assert len(fake_yellow.submitted_orders) == 1


def test_order_lifecycle_progresses_through_expected_states(
    client, test_intent, make_proof_bundle, fake_yellow
):
    """Submitted orders move through SUBMITTED → MATCHED → ESCROW_LOCKED → SETTLED."""
    bundle = make_proof_bundle(test_intent)
    submit = _submit(client, test_intent, receipt={"proof_bundle": bundle})
    assert submit.status_code == 200
    order_id = submit.json()["order_id"]

    expected_path = ["SUBMITTED", "MATCHED", "ESCROW_LOCKED", "SETTLED"]
    observed: list[str] = []
    for status in expected_path:
        fake_yellow.advance(order_id, status)
        resp = client.get(f"/v1/yellow/order/{order_id}/status")
        assert resp.status_code == 200
        observed.append(resp.json()["status"])

    assert observed == expected_path


def test_status_query_for_unknown_order_is_handled(client, fake_yellow):
    resp = client.get("/v1/yellow/order/does_not_exist/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("UNKNOWN", "FAILED")
