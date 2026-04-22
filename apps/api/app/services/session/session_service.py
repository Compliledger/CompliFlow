import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.models.session import SessionKey
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class SessionService:

    @staticmethod
    def validate_session(
        session_key: str,
        wallet: str,
        required_allowance: float = 0,
    ) -> Tuple[bool, Optional[str]]:
        if not session_key or not wallet:
            reason = "Missing session_key or wallet"
            AuditService.log_session_validation(session_key, wallet, False, reason)
            return False, reason

        try:
            with get_db() as db:
                record: Optional[SessionKey] = (
                    db.query(SessionKey)
                    .filter(
                        SessionKey.session_key == session_key,
                        SessionKey.wallet == wallet,
                    )
                    .first()
                )

                if record is None:
                    reason = "session_not_found"
                    AuditService.log_session_validation(session_key, wallet, False, reason)
                    return False, reason

                if not record.is_active:
                    reason = "session_revoked"
                    AuditService.log_session_validation(session_key, wallet, False, reason)
                    return False, reason

                now = datetime.utcnow()
                if now > record.expires_at:
                    reason = f"session_expired (expired at {record.expires_at.isoformat()})"
                    AuditService.log_session_validation(session_key, wallet, False, reason)
                    return False, reason

                if required_allowance > record.remaining_allowance:
                    reason = (
                        f"insufficient_allowance: required {required_allowance}, "
                        f"remaining {record.remaining_allowance}"
                    )
                    AuditService.log_session_validation(session_key, wallet, False, reason)
                    return False, reason

                AuditService.log_session_validation(session_key, wallet, True)
                logger.info(
                    "Session validated: session=%s wallet=%s allowance=%.2f",
                    session_key,
                    wallet,
                    record.remaining_allowance,
                )
                return True, None

        except SQLAlchemyError as exc:
            logger.error("DB error during session validation: %s", exc)
            reason = "database_error"
            AuditService.log_session_validation(session_key, wallet, False, reason)
            return False, reason

    @staticmethod
    def create_session(
        session_key: str,
        wallet: str,
        initial_allowance: float = 10000,
        validity_days: int = 30,
    ) -> dict:
        now = datetime.utcnow()
        expires_at = now + timedelta(days=validity_days)

        try:
            with get_db() as db:
                record = SessionKey(
                    session_key=session_key,
                    wallet=wallet,
                    expires_at=expires_at,
                    initial_allowance=initial_allowance,
                    remaining_allowance=initial_allowance,
                    is_active=True,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                session_dict = record.to_dict()

            AuditService.log_event(
                event_type="SESSION_CREATED",
                status="CREATED",
                session_key=session_key,
                wallet=wallet,
                details=session_dict,
            )
            logger.info("Session created: session=%s wallet=%s", session_key, wallet)
            return session_dict

        except SQLAlchemyError as exc:
            logger.error("DB error creating session: %s", exc)
            raise RuntimeError(f"Failed to create session: {exc}") from exc

    @staticmethod
    def consume_allowance(
        session_key: str,
        wallet: str,
        amount: float,
    ) -> Tuple[bool, Optional[str]]:
        try:
            with get_db() as db:
                record: Optional[SessionKey] = (
                    db.query(SessionKey)
                    .filter(
                        SessionKey.session_key == session_key,
                        SessionKey.wallet == wallet,
                    )
                    .first()
                )

                if record is None:
                    reason = "session_not_found"
                    AuditService.log_event(
                        event_type="ALLOWANCE_CONSUMED",
                        status="FAILED",
                        session_key=session_key,
                        wallet=wallet,
                        details={"amount": amount, "reason": reason},
                    )
                    return False, reason

                if amount > record.remaining_allowance:
                    reason = (
                        f"insufficient_allowance: {amount} > {record.remaining_allowance}"
                    )
                    AuditService.log_event(
                        event_type="ALLOWANCE_CONSUMED",
                        status="FAILED",
                        session_key=session_key,
                        wallet=wallet,
                        details={
                            "amount": amount,
                            "remaining": record.remaining_allowance,
                            "reason": reason,
                        },
                    )
                    return False, reason

                previous_remaining = record.remaining_allowance
                record.remaining_allowance -= amount
                record.last_used_at = datetime.utcnow()
                db.commit()

                AuditService.log_event(
                    event_type="ALLOWANCE_CONSUMED",
                    status="SUCCESS",
                    session_key=session_key,
                    wallet=wallet,
                    details={
                        "amount": amount,
                        "previous_remaining": previous_remaining,
                        "new_remaining": record.remaining_allowance,
                    },
                )
                logger.info(
                    "Allowance consumed: session=%s amount=%.2f remaining=%.2f",
                    session_key,
                    amount,
                    record.remaining_allowance,
                )
                return True, None

        except SQLAlchemyError as exc:
            logger.error("DB error consuming allowance: %s", exc)
            return False, f"database_error: {exc}"
