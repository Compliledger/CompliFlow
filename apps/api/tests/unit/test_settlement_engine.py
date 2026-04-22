"""Unit tests for the CompliFlow settlement engine."""

from __future__ import annotations

import time

import pytest

from app.services.proof.receipt_signer import ReceiptSigner
from app.services.settlement import settlement_engine as se


def _future_ts(seconds: int = 600) -> int:
    return int(time.time()) + seconds


def _past_ts(seconds: int = 600) -> int:
    return int(time.time()) - seconds


def _make_intent(**overrides) -> dict:
    base = {
        "session_key": "sess_abc",
        "user_wallet": "0x1111111111111111111111111111111111111111",
        "side": "BUY",
        "amount": 10.0,
        "price": 2.0,
        "asset": "ytest.usd",
        "expires_at": _future_ts(),
        "jurisdiction": "ALLOWED",
    }
    base.update(overrides)
    return base


def _signed_receipt(intent: dict) -> dict:
    return ReceiptSigner.sign({"intent": intent, "decision": {"decision": "ALLOW"}})


def _assert_shape(decision: dict) -> None:
    assert set(decision.keys()) == {
        "decision",
        "reason_codes",
        "human_reason",
        "conditions",
        "policy_version",
        "settlement_context",
    }
    assert decision["decision"] in (
        se.DECISION_ALLOW,
        se.DECISION_DENY,
        se.DECISION_ALLOW_WITH_CONDITIONS,
    )
    assert isinstance(decision["reason_codes"], list)
    assert isinstance(decision["human_reason"], str) and decision["human_reason"]
    assert "valid_until" in decision["conditions"]
    ctx = decision["settlement_context"]
    assert set(ctx.keys()) == {"order_id", "match_id", "proof_hash"}


def test_allow_with_conditions_when_match_ready():
    intent = _make_intent()
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=receipt,
        execution_status="MATCHED",
        proofs={"match_id": "m_1", "collateral_ok": True},
    )
    _assert_shape(decision)
    assert decision["decision"] == se.DECISION_ALLOW_WITH_CONDITIONS
    assert decision["reason_codes"] == []
    assert decision["conditions"]["valid_until"] == intent["expires_at"]
    assert decision["settlement_context"]["order_id"] == "order_1"
    assert decision["settlement_context"]["match_id"] == "m_1"
    assert decision["settlement_context"]["proof_hash"]


def test_deny_when_receipt_missing():
    intent = _make_intent()
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt={},
        execution_status="MATCHED",
    )
    _assert_shape(decision)
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_RECEIPT_MISSING in decision["reason_codes"]


def test_deny_when_receipt_signature_invalid():
    intent = _make_intent()
    receipt = _signed_receipt(intent)
    # Tamper with the payload so the signature no longer verifies.
    tampered = {
        "payload": {**receipt["payload"], "tampered": True},
        "signature": receipt["signature"],
    }
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=tampered,
        execution_status="MATCHED",
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_RECEIPT_INVALID in decision["reason_codes"]


def test_deny_when_execution_status_not_eligible():
    intent = _make_intent()
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=receipt,
        execution_status="SUBMITTED",
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_EXECUTION_STATUS_NOT_ELIGIBLE in decision["reason_codes"]


def test_deny_when_execution_status_unknown():
    intent = _make_intent()
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=receipt,
        execution_status="BOGUS",
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_EXECUTION_STATUS_INVALID in decision["reason_codes"]


def test_deny_when_jurisdiction_blocked():
    intent = _make_intent(jurisdiction="BLOCKED_REGION")
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=receipt,
        execution_status="ESCROW_LOCKED",
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_JURISDICTION_BLOCKED in decision["reason_codes"]


def test_deny_when_intent_expired():
    intent = _make_intent(expires_at=_past_ts())
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=receipt,
        execution_status="MATCHED",
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_INTENT_EXPIRED in decision["reason_codes"]


def test_deny_when_collateral_flag_false():
    intent = _make_intent()
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=receipt,
        execution_status="MATCHED",
        proofs={"collateral_ok": False},
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_COLLATERAL_INSUFFICIENT in decision["reason_codes"]


def test_collateral_flag_absent_does_not_deny():
    intent = _make_intent()
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=receipt,
        execution_status="MATCHED",
        proofs={},
    )
    assert decision["decision"] != se.DECISION_DENY


def test_deny_when_order_id_missing():
    intent = _make_intent()
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="",
        intent=intent,
        receipt=receipt,
        execution_status="MATCHED",
    )
    assert decision["decision"] == se.DECISION_DENY
    assert se.REASON_ORDER_ID_MISSING in decision["reason_codes"]


def test_settlement_context_uses_explicit_proof_hash():
    intent = _make_intent()
    receipt = _signed_receipt(intent)
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt=receipt,
        execution_status="MATCHED",
        proofs={"proof_hash": "deadbeef", "match_id": "m_42"},
    )
    assert decision["settlement_context"]["proof_hash"] == "deadbeef"
    assert decision["settlement_context"]["match_id"] == "m_42"


def test_multiple_failures_aggregate_reason_codes():
    intent = _make_intent(jurisdiction="BLOCKED_REGION", expires_at=_past_ts())
    decision = se.SettlementEngine.evaluate(
        order_id="order_1",
        intent=intent,
        receipt={},
        execution_status="SUBMITTED",
    )
    codes = set(decision["reason_codes"])
    assert se.REASON_RECEIPT_MISSING in codes
    assert se.REASON_EXECUTION_STATUS_NOT_ELIGIBLE in codes
    assert se.REASON_JURISDICTION_BLOCKED in codes
    assert se.REASON_INTENT_EXPIRED in codes
