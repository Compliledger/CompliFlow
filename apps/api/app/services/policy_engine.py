from typing import List

from app.models.intent import TradeIntent

BLOCKED_JURISDICTIONS = ["BLOCKED_REGION"]


class PolicyEngine:

    @staticmethod
    def evaluate_credential(jurisdiction: str, assets: List[str], max_notional: float) -> dict:
        if jurisdiction in BLOCKED_JURISDICTIONS:
            return {"status": "FAIL", "reason": "Jurisdiction restricted"}
        if max_notional <= 0:
            return {"status": "FAIL", "reason": "Invalid max_notional"}
        return {"status": "PASS"}

    @staticmethod
    def evaluate(intent: TradeIntent) -> dict:
        # Rule 1: Amount must be positive
        if intent.amount <= 0:
            return {"status": "FAIL", "reason": "Invalid amount"}

        # Rule 2: Price must be positive
        if intent.price <= 0:
            return {"status": "FAIL", "reason": "Invalid price"}

        # Rule 3: Side validation
        if intent.side not in ["BUY", "SELL"]:
            return {"status": "FAIL", "reason": "Invalid side"}

        # Rule 4: Jurisdiction block example
        if intent.jurisdiction in BLOCKED_JURISDICTIONS:
            return {"status": "FAIL", "reason": "Jurisdiction restricted"}

        return {"status": "PASS"}
