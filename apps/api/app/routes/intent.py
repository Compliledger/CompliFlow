from fastapi import APIRouter, HTTPException
from app.models.intent import TradeIntent
from app.services.policy_engine import PolicyEngine
from app.services.receipt_signer import ReceiptSigner
from app.services.session_service import SessionService
from app.services.audit_service import AuditService
import uuid

router = APIRouter()

@router.post("/evaluate")
async def evaluate_intent(intent: TradeIntent):
    required_allowance = intent.amount * intent.price
    is_valid, reason = SessionService.validate_session(
        session_key=intent.session_key,
        wallet=intent.user_wallet,
        required_allowance=required_allowance,
    )

    if not is_valid:
        # Preserve previous API behavior: session failures still return 403.
        # We also surface the policy-engine deny shape inside the detail so
        # callers migrating to the new format have something consistent.
        denied = PolicyEngine.evaluate(
            intent,
            session_valid=False,
            session_reason=reason,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Session validation failed",
                "reason": reason,
                "decision": denied,
            },
        )

    decision = PolicyEngine.evaluate(intent)

    receipt_payload = {
        "intent": intent.dict(),
        "decision": decision
    }

    signed_receipt = ReceiptSigner.sign(receipt_payload)
    receipt_hash = AuditService.compute_receipt_hash(receipt_payload)
    
    AuditService.log_intent_evaluation(
        intent=intent.dict(),
        decision=decision,
        receipt_hash=receipt_hash
    )
    
    signed_receipt["receipt_hash"] = receipt_hash
    signed_receipt["order_id"] = f"order_{uuid.uuid4().hex[:12]}"
    
    return signed_receipt
