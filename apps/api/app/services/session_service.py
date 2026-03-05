from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.services.audit_service import AuditService


class SessionService:
    @staticmethod
    def validate_session(
        session_key: str,
        wallet: str,
        required_allowance: float = 0
    ) -> Tuple[bool, Optional[str]]:
        if not session_key or not wallet:
            reason = "Missing session_key or wallet"
            AuditService.log_session_validation(session_key, wallet, False, reason)
            return False, reason
        
        session_data = {
            "session_key": session_key,
            "wallet": wallet,
            "expires_at": datetime.utcnow() + timedelta(days=30),
            "remaining_allowance": 10000
        }
        
        now = datetime.utcnow()
        expires_at = session_data.get("expires_at")
        
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        
        if now > expires_at:
            reason = f"Session expired at {expires_at.isoformat()}"
            AuditService.log_session_validation(session_key, wallet, False, reason)
            return False, reason
        
        remaining_allowance = session_data.get("remaining_allowance", 0)
        if required_allowance > remaining_allowance:
            reason = f"Insufficient allowance: required {required_allowance}, remaining {remaining_allowance}"
            AuditService.log_session_validation(session_key, wallet, False, reason)
            return False, reason
        
        AuditService.log_session_validation(session_key, wallet, True)
        return True, None
    
    @staticmethod
    def create_session(
        session_key: str,
        wallet: str,
        initial_allowance: float = 10000,
        validity_days: int = 30
    ) -> dict:
        now = datetime.utcnow()
        expires_at = now + timedelta(days=validity_days)
        
        session = {
            "session_key": session_key,
            "wallet": wallet,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "initial_allowance": initial_allowance,
            "remaining_allowance": initial_allowance,
            "is_active": True
        }
        
        AuditService.log_event(
            event_type="SESSION_CREATED",
            status="CREATED",
            session_key=session_key,
            wallet=wallet,
            details=session
        )
        
        return session
    
    @staticmethod
    def consume_allowance(
        session_key: str,
        wallet: str,
        amount: float
    ) -> Tuple[bool, Optional[str]]:
        session_data = {
            "session_key": session_key,
            "wallet": wallet,
            "remaining_allowance": 10000
        }
        
        remaining = session_data.get("remaining_allowance", 0)
        
        if amount > remaining:
            reason = f"Insufficient allowance: {amount} > {remaining}"
            AuditService.log_event(
                event_type="ALLOWANCE_CONSUMED",
                status="FAILED",
                session_key=session_key,
                wallet=wallet,
                details={"amount": amount, "remaining": remaining, "reason": reason}
            )
            return False, reason
        
        new_remaining = remaining - amount
        
        AuditService.log_event(
            event_type="ALLOWANCE_CONSUMED",
            status="SUCCESS",
            session_key=session_key,
            wallet=wallet,
            details={
                "amount": amount,
                "previous_remaining": remaining,
                "new_remaining": new_remaining
            }
        )
        
        return True, None
