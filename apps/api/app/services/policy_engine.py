from app.models.intent import TradeIntent

class PolicyEngine:

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
        if intent.jurisdiction == "BLOCKED_REGION":
            return {"status": "FAIL", "reason": "Jurisdiction restricted"}

        return {"status": "PASS"}
