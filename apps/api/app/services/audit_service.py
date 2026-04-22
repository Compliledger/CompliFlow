import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


# Canonical event types for the trade lifecycle. They are exposed as
# constants so callers (and tests) can refer to them symbolically.
EVENT_INTENT_EVALUATED = "INTENT_EVALUATED"
EVENT_DECISION_EVALUATED = "DECISION_EVALUATED"
EVENT_PROOF_GENERATED = "PROOF_GENERATED"
EVENT_ORDER_SUBMITTED = "ORDER_SUBMITTED"
EVENT_ORDER_STATUS_CHANGE = "ORDER_STATUS_CHANGE"
EVENT_EXECUTION_TRANSITION = "EXECUTION_TRANSITION"
EVENT_SETTLEMENT_VALIDATED = "SETTLEMENT_VALIDATED"
EVENT_SESSION_VALIDATION = "SESSION_VALIDATION"


def _coerce_reason_codes(reason_codes: Any) -> Optional[List[str]]:
    if reason_codes is None:
        return None
    if isinstance(reason_codes, str):
        return [reason_codes]
    if isinstance(reason_codes, Iterable):
        return [str(c) for c in reason_codes]
    return [str(reason_codes)]


class AuditService:
    @staticmethod
    def log_event(
        event_type: str,
        status: str,
        order_id: Optional[str] = None,
        session_key: Optional[str] = None,
        wallet: Optional[str] = None,
        receipt_hash: Optional[str] = None,
        details: Optional[dict] = None,
        *,
        event_status: Optional[str] = None,
        proof_hash: Optional[str] = None,
        policy_version: Optional[str] = None,
        reason_codes: Optional[Iterable[str]] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Persist a single audit event.

        ``status`` remains required for backward compatibility with existing
        callers. ``event_status`` is the upgraded name for the same field and
        defaults to ``status`` when not supplied.
        """
        now = datetime.utcnow()
        effective_status = event_status or status
        normalized_reasons = _coerce_reason_codes(reason_codes)

        audit_entry = {
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
            "event_type": event_type,
            "status": status,
            "event_status": effective_status,
            "order_id": order_id,
            "session_key": session_key,
            "wallet": wallet,
            "receipt_hash": receipt_hash,
            "proof_hash": proof_hash,
            "policy_version": policy_version,
            "reason_codes": normalized_reasons,
            "details": details or {},
            "metadata": metadata,
        }

        logger.info(
            "[AUDIT] event=%s status=%s order_id=%s session=%s wallet=%s "
            "proof_hash=%s policy_version=%s reason_codes=%s",
            event_type,
            effective_status,
            order_id,
            session_key,
            wallet,
            proof_hash,
            policy_version,
            normalized_reasons,
        )

        try:
            from app.db.session import get_db

            with get_db() as db:
                record = AuditLog(
                    timestamp=now,
                    created_at=now,
                    event_type=event_type,
                    status=status,
                    event_status=effective_status,
                    order_id=order_id,
                    session_key=session_key,
                    wallet=wallet,
                    receipt_hash=receipt_hash,
                    proof_hash=proof_hash,
                    policy_version=policy_version,
                    reason_codes=normalized_reasons,
                    details=details or {},
                    event_metadata=metadata,
                )
                db.add(record)
                db.commit()
        except Exception as exc:
            logger.error("Failed to persist audit log to DB: %s", exc)

        return audit_entry

    @staticmethod
    def compute_receipt_hash(receipt: dict) -> str:
        receipt_str = json.dumps(receipt, sort_keys=True)
        return hashlib.sha256(receipt_str.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    @staticmethod
    def log_decision(
        intent: Dict[str, Any],
        decision: Dict[str, Any],
        receipt_hash: Optional[str] = None,
        order_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Audit a policy / decision-engine evaluation.

        Extracts ``policy_version`` and ``reason_codes`` from the decision
        envelope produced by the enforcement engine.
        """
        status = decision.get("decision") or decision.get("status", "UNKNOWN")
        return AuditService.log_event(
            event_type=EVENT_DECISION_EVALUATED,
            status=status,
            order_id=order_id,
            session_key=intent.get("session_key"),
            wallet=intent.get("user_wallet") or intent.get("wallet"),
            receipt_hash=receipt_hash,
            policy_version=decision.get("policy_version"),
            reason_codes=decision.get("reason_codes"),
            details={
                "intent": intent,
                "decision": decision,
            },
            metadata=metadata,
        )

    @staticmethod
    def log_intent_evaluation(intent: dict, decision: dict, receipt_hash: str):
        # ``decision`` follows the enforcement-engine shape:
        #   {"decision": "ALLOW"|"DENY"|"ALLOW_WITH_CONDITIONS", ...}
        # Fall back to the legacy ``status`` field for backwards compatibility.
        status = decision.get("decision") or decision.get("status", "UNKNOWN")
        return AuditService.log_event(
            event_type=EVENT_INTENT_EVALUATED,
            status=status,
            session_key=intent.get("session_key"),
            wallet=intent.get("user_wallet"),
            receipt_hash=receipt_hash,
            policy_version=decision.get("policy_version"),
            reason_codes=decision.get("reason_codes"),
            details={
                "intent": intent,
                "decision": decision
            }
        )

    @staticmethod
    def log_proof_generated(
        order_id: Optional[str],
        proof_hash: str,
        proof_type: Optional[str] = None,
        session_key: Optional[str] = None,
        wallet: Optional[str] = None,
        details: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Audit a proof / receipt-hash generation step."""
        return AuditService.log_event(
            event_type=EVENT_PROOF_GENERATED,
            status="GENERATED",
            order_id=order_id,
            session_key=session_key,
            wallet=wallet,
            proof_hash=proof_hash,
            details={
                "proof_type": proof_type,
                **(details or {}),
            },
            metadata=metadata,
        )

    @staticmethod
    def log_order_submission(order_id: str, session_key: str, wallet: str, yellow_order_id: str):
        return AuditService.log_event(
            event_type=EVENT_ORDER_SUBMITTED,
            status="SUBMITTED",
            order_id=order_id,
            session_key=session_key,
            wallet=wallet,
            details={
                "yellow_order_id": yellow_order_id
            }
        )

    @staticmethod
    def log_order_status_change(order_id: str, old_status: str, new_status: str, details: dict = None):
        return AuditService.log_event(
            event_type=EVENT_ORDER_STATUS_CHANGE,
            status=new_status,
            order_id=order_id,
            details={
                "old_status": old_status,
                "new_status": new_status,
                **(details or {})
            }
        )

    @staticmethod
    def log_execution_transition(
        order_id: str,
        from_status: Optional[str],
        to_status: str,
        proof_hash: Optional[str] = None,
        session_key: Optional[str] = None,
        wallet: Optional[str] = None,
        details: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Audit a transition through the execution state machine
        (e.g. SUBMITTED → MATCHED → ESCROW_LOCKED → SETTLED)."""
        return AuditService.log_event(
            event_type=EVENT_EXECUTION_TRANSITION,
            status=to_status,
            order_id=order_id,
            session_key=session_key,
            wallet=wallet,
            proof_hash=proof_hash,
            details={
                "from_status": from_status,
                "to_status": to_status,
                **(details or {}),
            },
            metadata=metadata,
        )

    @staticmethod
    def log_session_validation(session_key: str, wallet: str, is_valid: bool, reason: str = None):
        return AuditService.log_event(
            event_type=EVENT_SESSION_VALIDATION,
            status="VALID" if is_valid else "INVALID",
            session_key=session_key,
            wallet=wallet,
            details={
                "is_valid": is_valid,
                "reason": reason
            }
        )

    @staticmethod
    def log_settlement_validation(
        order_id: str,
        decision: dict,
        execution_status: Optional[str] = None,
        intent: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        """Persist a settlement validation decision to the audit log.

        Pulls ``policy_version``, ``reason_codes`` and the ``proof_hash``
        out of the settlement engine's response so they are available as
        first-class audit columns.
        """
        status = decision.get("decision", "UNKNOWN")
        wallet = (intent or {}).get("user_wallet")
        session_key = (intent or {}).get("session_key")
        settlement_ctx = decision.get("settlement_context") or {}
        proof_hash = settlement_ctx.get("proof_hash")
        return AuditService.log_event(
            event_type=EVENT_SETTLEMENT_VALIDATED,
            status=status,
            order_id=order_id,
            session_key=session_key,
            wallet=wallet,
            proof_hash=proof_hash,
            policy_version=decision.get("policy_version"),
            reason_codes=decision.get("reason_codes"),
            details={
                "execution_status": execution_status,
                "decision": decision,
            },
            metadata=metadata,
        )
