"""Unit tests for the upgraded AuditService lifecycle helpers.

These tests focus on the in-memory entry returned by ``log_event`` and the
helper methods so they don't depend on the database. The real DB write is
exercised by the integration suite.
"""

from unittest.mock import patch

import pytest

from app.services import audit_service as audit_module
from app.services.audit_service import AuditService


@pytest.fixture(autouse=True)
def _silence_db():
    """Stop the audit service from touching the DB during these unit tests."""
    with patch.object(audit_module, "AuditLog") as fake_model, \
         patch("app.db.session.get_db") as fake_get_db:
        # Make ``with get_db() as db:`` work with a no-op session.
        class _Session:
            def add(self, *_a, **_k):
                pass

            def commit(self):
                pass

        class _Ctx:
            def __enter__(self_inner):
                return _Session()

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        fake_get_db.return_value = _Ctx()
        fake_model.side_effect = lambda **kwargs: kwargs  # ignore construction
        yield


def test_log_event_populates_new_fields():
    entry = AuditService.log_event(
        event_type="DECISION_EVALUATED",
        status="ALLOW",
        order_id="order_123",
        proof_hash="abc123",
        policy_version="policy.v1",
        reason_codes=["SOME_CODE"],
        metadata={"correlation_id": "xyz"},
    )

    assert entry["event_type"] == "DECISION_EVALUATED"
    assert entry["status"] == "ALLOW"
    assert entry["event_status"] == "ALLOW"
    assert entry["order_id"] == "order_123"
    assert entry["proof_hash"] == "abc123"
    assert entry["policy_version"] == "policy.v1"
    assert entry["reason_codes"] == ["SOME_CODE"]
    assert entry["metadata"] == {"correlation_id": "xyz"}
    assert entry["timestamp"] == entry["created_at"]


def test_log_event_event_status_overrides_status_field():
    entry = AuditService.log_event(
        event_type="FOO",
        status="LEGACY",
        event_status="UPGRADED",
    )
    # Legacy ``status`` is preserved so old readers keep working...
    assert entry["status"] == "LEGACY"
    # ...while the new column carries the explicit override.
    assert entry["event_status"] == "UPGRADED"


def test_log_event_normalizes_string_reason_codes():
    entry = AuditService.log_event(
        event_type="FOO",
        status="DENY",
        reason_codes="JUST_ONE",
    )
    assert entry["reason_codes"] == ["JUST_ONE"]


def test_log_decision_extracts_policy_metadata():
    intent = {"session_key": "sess_1", "user_wallet": "0xabc"}
    decision = {
        "decision": "DENY",
        "reason_codes": ["ALLOWANCE_INSUFFICIENT"],
        "policy_version": "policy.v2",
    }

    entry = AuditService.log_decision(intent, decision, receipt_hash="rh", order_id="o1")

    assert entry["event_type"] == audit_module.EVENT_DECISION_EVALUATED
    assert entry["status"] == "DENY"
    assert entry["session_key"] == "sess_1"
    assert entry["wallet"] == "0xabc"
    assert entry["receipt_hash"] == "rh"
    assert entry["order_id"] == "o1"
    assert entry["policy_version"] == "policy.v2"
    assert entry["reason_codes"] == ["ALLOWANCE_INSUFFICIENT"]
    assert entry["details"]["intent"] == intent
    assert entry["details"]["decision"] == decision


def test_log_proof_generated_sets_proof_hash():
    entry = AuditService.log_proof_generated(
        order_id="o1",
        proof_hash="deadbeef",
        proof_type="receipt-sha256",
        session_key="sess",
        wallet="0xabc",
    )
    assert entry["event_type"] == audit_module.EVENT_PROOF_GENERATED
    assert entry["status"] == "GENERATED"
    assert entry["proof_hash"] == "deadbeef"
    assert entry["details"]["proof_type"] == "receipt-sha256"


def test_log_execution_transition_records_state_change():
    entry = AuditService.log_execution_transition(
        order_id="o1",
        from_status="SUBMITTED",
        to_status="MATCHED",
        proof_hash="ph",
    )
    assert entry["event_type"] == audit_module.EVENT_EXECUTION_TRANSITION
    assert entry["status"] == "MATCHED"
    assert entry["proof_hash"] == "ph"
    assert entry["details"] == {
        "from_status": "SUBMITTED",
        "to_status": "MATCHED",
    }


def test_log_settlement_validation_extracts_proof_and_policy():
    decision = {
        "decision": "ALLOW",
        "reason_codes": [],
        "policy_version": "settlement.v1",
        "settlement_context": {
            "order_id": "o1",
            "match_id": "m1",
            "proof_hash": "phash",
        },
    }

    entry = AuditService.log_settlement_validation(
        order_id="o1",
        decision=decision,
        execution_status="MATCHED",
        intent={"session_key": "sess", "user_wallet": "0xabc"},
    )

    assert entry["event_type"] == audit_module.EVENT_SETTLEMENT_VALIDATED
    assert entry["status"] == "ALLOW"
    assert entry["proof_hash"] == "phash"
    assert entry["policy_version"] == "settlement.v1"
    assert entry["reason_codes"] == []
    assert entry["details"]["execution_status"] == "MATCHED"
    assert entry["session_key"] == "sess"
    assert entry["wallet"] == "0xabc"


def test_log_intent_evaluation_still_works_and_now_carries_policy_metadata():
    intent = {"session_key": "s", "user_wallet": "w"}
    decision = {
        "decision": "ALLOW",
        "reason_codes": [],
        "policy_version": "policy.v1",
    }
    entry = AuditService.log_intent_evaluation(intent, decision, receipt_hash="rh")
    assert entry["event_type"] == audit_module.EVENT_INTENT_EVALUATED
    assert entry["status"] == "ALLOW"
    assert entry["receipt_hash"] == "rh"
    assert entry["policy_version"] == "policy.v1"
    assert entry["reason_codes"] == []
