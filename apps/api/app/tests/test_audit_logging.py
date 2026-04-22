"""End-to-end audit-log coverage for the major lifecycle events."""

from __future__ import annotations


def _filter_event_types(logs):
    return {log["event_type"] for log in logs}


def test_intent_evaluation_writes_audit_entry(client, test_intent):
    response = client.post("/v1/intent/evaluate", json=test_intent)
    assert response.status_code == 200

    audit = client.get(
        "/v1/audit/logs",
        params={"session_key": test_intent["session_key"]},
    ).json()
    types = _filter_event_types(audit["logs"])
    # Both the session validation and the intent evaluation are audited.
    assert "SESSION_VALIDATION" in types
    assert "INTENT_EVALUATED" in types


def test_order_submission_writes_lifecycle_entries(
    client, test_intent, make_proof_bundle, fake_yellow
):
    bundle = make_proof_bundle(test_intent)
    submit = client.post(
        "/v1/yellow/order/submit",
        json={"intent": test_intent, "receipt": {"proof_bundle": bundle}},
    )
    assert submit.status_code == 200
    order_id = submit.json()["order_id"]

    trail = client.get(f"/v1/audit/logs/{order_id}").json()
    assert trail["order_id"] == order_id
    types = _filter_event_types(trail["audit_trail"])
    # Both the submission event and the SUBMITTED status change are recorded.
    assert "ORDER_SUBMITTED" in types
    assert "ORDER_STATUS_CHANGE" in types


def test_settlement_validation_writes_audit_entry(client, test_intent):
    from app.services.proof.receipt_signer import ReceiptSigner

    receipt = ReceiptSigner.sign({"intent": test_intent, "decision": {"decision": "ALLOW"}})
    resp = client.post(
        "/v1/settlement/validate",
        json={
            "order_id": "ord_audit",
            "intent": test_intent,
            "receipt": receipt,
            "execution_status": "MATCHED",
        },
    )
    assert resp.status_code == 200

    audit = client.get(
        "/v1/audit/logs",
        params={"order_id": "ord_audit"},
    ).json()
    assert any(log["event_type"] == "SETTLEMENT_VALIDATED" for log in audit["logs"])


def test_failed_session_validation_is_audited(client):
    """A bogus session must still produce a SESSION_VALIDATION audit entry."""
    bogus_intent = {
        "session_key": "no_such_session",
        "user_wallet": "0x" + "0" * 40,
        "side": "BUY",
        "asset": "ytest.usd",
        "amount": 1,
        "price": 1.0,
        "jurisdiction": "ALLOWED",
        "expires_at": 9999999999,
    }
    response = client.post("/v1/intent/evaluate", json=bogus_intent)
    assert response.status_code == 403

    audit = client.get(
        "/v1/audit/logs",
        params={"session_key": "no_such_session"},
    ).json()
    types = _filter_event_types(audit["logs"])
    assert "SESSION_VALIDATION" in types
    # The denied entry must record an INVALID status (not VALID).
    invalid_entries = [
        log for log in audit["logs"]
        if log["event_type"] == "SESSION_VALIDATION"
    ]
    assert any(entry["status"] == "INVALID" for entry in invalid_entries)
