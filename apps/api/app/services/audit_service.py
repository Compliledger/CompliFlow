import hashlib
import json
import logging
from datetime import datetime

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    def log_event(
        event_type: str,
        status: str,
        order_id: str = None,
        session_key: str = None,
        wallet: str = None,
        receipt_hash: str = None,
        details: dict = None,
    ) -> dict:
        now = datetime.utcnow()
        audit_entry = {
            "timestamp": now.isoformat(),
            "event_type": event_type,
            "status": status,
            "order_id": order_id,
            "session_key": session_key,
            "wallet": wallet,
            "receipt_hash": receipt_hash,
            "details": details or {},
        }

        logger.info(
            "[AUDIT] event=%s status=%s order_id=%s session=%s wallet=%s",
            event_type,
            status,
            order_id,
            session_key,
            wallet,
        )

        try:
            from app.db.session import get_db

            with get_db() as db:
                record = AuditLog(
                    timestamp=now,
                    event_type=event_type,
                    status=status,
                    order_id=order_id,
                    session_key=session_key,
                    wallet=wallet,
                    receipt_hash=receipt_hash,
                    details=details or {},
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
    
    @staticmethod
    def log_intent_evaluation(intent: dict, decision: dict, receipt_hash: str):
        # ``decision`` follows the enforcement-engine shape:
        #   {"decision": "ALLOW"|"DENY"|"ALLOW_WITH_CONDITIONS", ...}
        # Fall back to the legacy ``status`` field for backwards compatibility.
        status = decision.get("decision") or decision.get("status", "UNKNOWN")
        return AuditService.log_event(
            event_type="INTENT_EVALUATED",
            status=status,
            session_key=intent.get("session_key"),
            wallet=intent.get("user_wallet"),
            receipt_hash=receipt_hash,
            details={
                "intent": intent,
                "decision": decision
            }
        )
    
    @staticmethod
    def log_order_submission(order_id: str, session_key: str, wallet: str, yellow_order_id: str):
        return AuditService.log_event(
            event_type="ORDER_SUBMITTED",
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
            event_type="ORDER_STATUS_CHANGE",
            status=new_status,
            order_id=order_id,
            details={
                "old_status": old_status,
                "new_status": new_status,
                **(details or {})
            }
        )
    
    @staticmethod
    def log_session_validation(session_key: str, wallet: str, is_valid: bool, reason: str = None):
        return AuditService.log_event(
            event_type="SESSION_VALIDATION",
            status="VALID" if is_valid else "INVALID",
            session_key=session_key,
            wallet=wallet,
            details={
                "is_valid": is_valid,
                "reason": reason
            }
        )
