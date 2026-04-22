"""Tests for the settlement validation endpoint and engine."""

from __future__ import annotations

import base64
import json
import time

from app.services.proof.receipt_signer import private_key
from app.services.settlement import settlement_engine as se


def _engine_compatible_receipt(intent: dict) -> dict:
    """Sign a receipt in exactly the format ``SettlementEngine`` verifies.

    The settlement engine's ``_verify_receipt`` re-encodes the payload with
    ``json.dumps(payload, sort_keys=True)`` (default separators) before
    checking the signature, so we sign that same byte string here.
    """
    payload = {"intent": intent, "decision": {"decision": "ALLOW"}}
    message = json.dumps(payload, sort_keys=True).encode()
    signature = private_key.sign(message)
    return {"payload": payload, "signature": base64.b64encode(signature).decode()}


# ---------------------------------------------------------------------------
# Engine-level tests (cheap, no HTTP)
# ---------------------------------------------------------------------------

def test_engine_allows_matched_trade_with_valid_receipt(test_intent):
    receipt = _engine_compatible_receipt(test_intent)
    decision = se.SettlementEngine.evaluate(
        order_id="ord_1",
        intent=test_intent,
        receipt=receipt,
        execution_status="MATCHED",
        proofs={"match_id": "m_1", "collateral_ok": True},
    )
    assert decision["decision"] == se.DECISION_ALLOW_WITH_CONDITIONS
    assert decision["reason_codes"] == []
    assert decision["settlement_context"]["order_id"] == "ord_1"
    assert decision["settlement_context"]["match_id"] == "m_1"


def test_engine_denies_when_receipt_missing(test_intent):
    decision = se.SettlementEngine.evaluate(
        order_id="ord_1",
        intent=test_intent,
        receipt={},
        execution_status="MATCHED",
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_RECEIPT_MISSING in decision["reason_codes"]


def test_engine_denies_when_execution_status_not_eligible(test_intent):
    receipt = _engine_compatible_receipt(test_intent)
    decision = se.SettlementEngine.evaluate(
        order_id="ord_1",
        intent=test_intent,
        receipt=receipt,
        execution_status="SUBMITTED",  # too early
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_EXECUTION_STATUS_NOT_ELIGIBLE in decision["reason_codes"]


def test_engine_denies_when_intent_expired(test_intent):
    expired_intent = {**test_intent, "expires_at": int(time.time()) - 60}
    receipt = _engine_compatible_receipt(expired_intent)
    decision = se.SettlementEngine.evaluate(
        order_id="ord_1",
        intent=expired_intent,
        receipt=receipt,
        execution_status="MATCHED",
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_INTENT_EXPIRED in decision["reason_codes"]


# ---------------------------------------------------------------------------
# Route-level test exercising the full request → audit pipeline
# ---------------------------------------------------------------------------

def test_settlement_route_returns_decision_and_persists_audit(client, test_intent):
    receipt = _engine_compatible_receipt(test_intent)
    response = client.post(
        "/v1/settlement/validate",
        json={
            "order_id": "ord_route_1",
            "intent": test_intent,
            "receipt": receipt,
            "execution_status": "MATCHED",
            "proofs": {"match_id": "m_42", "collateral_ok": True},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] in (
        se.DECISION_ALLOW,
        se.DECISION_ALLOW_WITH_CONDITIONS,
    )
    assert body["settlement_context"]["order_id"] == "ord_route_1"

    audit = client.get(
        "/v1/audit/logs",
        params={"order_id": "ord_route_1", "event_type": "SETTLEMENT_VALIDATED"},
    )
    assert audit.status_code == 200
    logs = audit.json()["logs"]
    assert any(log["event_type"] == "SETTLEMENT_VALIDATED" for log in logs)


def test_settlement_route_returns_deny_for_missing_receipt(client, test_intent):
    response = client.post(
        "/v1/settlement/validate",
        json={
            "order_id": "ord_route_2",
            "intent": test_intent,
            "receipt": {},
            "execution_status": "MATCHED",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == se.DECISION_DENY
    assert se.REASON_RECEIPT_MISSING in body["reason_codes"]
