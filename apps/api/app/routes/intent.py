from fastapi import APIRouter
from app.models.intent import TradeIntent
from app.services.policy_engine import PolicyEngine
from app.services.receipt_signer import ReceiptSigner

router = APIRouter()

@router.post("/evaluate")
def evaluate_intent(intent: TradeIntent):
    decision = PolicyEngine.evaluate(intent)

    receipt_payload = {
        "intent": intent.dict(),
        "decision": decision
    }

    signed_receipt = ReceiptSigner.sign(receipt_payload)

    return signed_receipt
