"""CompliFlow policy / enforcement engine.

Produces structured, auditable decisions for a :class:`TradeIntent`. The output
shape is intentionally fixed so downstream systems (receipts, audit log, UI)
can rely on it::

    {
        "decision": "ALLOW" | "DENY" | "ALLOW_WITH_CONDITIONS",
        "reason_codes": ["..."],
        "human_reason": "string",
        "conditions": {
            "max_notional": float | None,
            "valid_until": int | None,           # unix timestamp (seconds)
            "allowed_assets": list[str] | None,
            "allowed_counterparties": list[str] | None,
        },
        "policy_version": "string",
    }

Reason codes are deterministic, machine-readable identifiers; ``human_reason``
is a friendlier sentence for UIs and logs.
"""

from __future__ import annotations

from typing import Optional

from app.models.intent import TradeIntent

from . import rules as _rules

__all__ = [
    "PolicyEngine",
    "DECISION_ALLOW",
    "DECISION_DENY",
    "DECISION_ALLOW_WITH_CONDITIONS",
]

DECISION_ALLOW = "ALLOW"
DECISION_DENY = "DENY"
DECISION_ALLOW_WITH_CONDITIONS = "ALLOW_WITH_CONDITIONS"

# Deterministic reason codes. Kept as module-level constants so callers and
# tests can import them rather than relying on string literals.
REASON_AMOUNT_INVALID = "AMOUNT_INVALID"
REASON_PRICE_INVALID = "PRICE_INVALID"
REASON_SIDE_INVALID = "SIDE_INVALID"
REASON_JURISDICTION_BLOCKED = "JURISDICTION_BLOCKED"
REASON_SESSION_INVALID = "SESSION_INVALID"
REASON_ALLOWANCE_INSUFFICIENT = "ALLOWANCE_INSUFFICIENT"
REASON_ASSET_NOT_ALLOWED = "ASSET_NOT_ALLOWED"
REASON_ORDER_SIZE_EXCEEDED = "ORDER_SIZE_EXCEEDED"

# Human-readable text for each deterministic reason code.
_REASON_TEXT: dict[str, str] = {
    REASON_AMOUNT_INVALID: "Amount must be greater than zero.",
    REASON_PRICE_INVALID: "Price must be greater than zero.",
    REASON_SIDE_INVALID: "Side must be one of: " + ", ".join(_rules.VALID_SIDES) + ".",
    REASON_JURISDICTION_BLOCKED: "Jurisdiction is blocked by policy.",
    REASON_SESSION_INVALID: "Session is not valid.",
    REASON_ALLOWANCE_INSUFFICIENT: "Session allowance is insufficient for this order.",
    REASON_ASSET_NOT_ALLOWED: "Asset is not on the allowlist.",
    REASON_ORDER_SIZE_EXCEEDED: "Order notional exceeds the configured maximum.",
}


def _empty_conditions() -> dict:
    return {
        "max_notional": None,
        "valid_until": None,
        "allowed_assets": None,
        "allowed_counterparties": None,
    }


def _build_decision(
    decision: str,
    reason_codes: list[str],
    conditions: dict,
    extra_human_reason: Optional[str] = None,
) -> dict:
    if reason_codes:
        human = "; ".join(
            _REASON_TEXT.get(code, code) for code in reason_codes
        )
    elif extra_human_reason:
        human = extra_human_reason
    else:
        human = "Order allowed."

    return {
        "decision": decision,
        "reason_codes": list(reason_codes),
        "human_reason": human,
        "conditions": conditions,
        "policy_version": _rules.POLICY_VERSION,
    }


class PolicyEngine:
    """Stateless evaluator that turns a :class:`TradeIntent` into a decision."""

    @staticmethod
    def evaluate(
        intent: TradeIntent,
        *,
        session_valid: bool = True,
        session_reason: Optional[str] = None,
        remaining_allowance: Optional[float] = None,
    ) -> dict:
        """Evaluate ``intent`` and return a structured decision dict.

        Parameters
        ----------
        intent:
            The trade intent to evaluate.
        session_valid:
            Whether the caller has already verified the session. ``False``
            triggers a ``SESSION_INVALID`` deny.
        session_reason:
            Optional human reason from session validation, surfaced when the
            session check fails.
        remaining_allowance:
            Remaining session allowance, in the same units as
            ``amount * price``. When provided and below the order notional, an
            ``ALLOWANCE_INSUFFICIENT`` deny is produced.
        """

        deny_codes: list[str] = []

        # Rule 1: amount > 0
        if intent.amount is None or intent.amount <= 0:
            deny_codes.append(REASON_AMOUNT_INVALID)

        # Rule 2: price > 0
        if intent.price is None or intent.price <= 0:
            deny_codes.append(REASON_PRICE_INVALID)

        # Rule 3: side valid
        if intent.side not in _rules.VALID_SIDES:
            deny_codes.append(REASON_SIDE_INVALID)

        # Rule 4: jurisdiction not blocked
        if intent.jurisdiction and intent.jurisdiction in _rules.BLOCKED_JURISDICTIONS:
            deny_codes.append(REASON_JURISDICTION_BLOCKED)

        # Rule 5: asset allowlist (when configured)
        if _rules.ALLOWED_ASSETS and intent.asset not in _rules.ALLOWED_ASSETS:
            deny_codes.append(REASON_ASSET_NOT_ALLOWED)

        # Rule 6: optional max order size (only meaningful when amount/price valid)
        notional: Optional[float] = None
        if (
            _rules.MAX_ORDER_NOTIONAL is not None
            and REASON_AMOUNT_INVALID not in deny_codes
            and REASON_PRICE_INVALID not in deny_codes
        ):
            notional = float(intent.amount) * float(intent.price)
            if notional > _rules.MAX_ORDER_NOTIONAL:
                deny_codes.append(REASON_ORDER_SIZE_EXCEEDED)

        # Rule 7: session valid
        if not session_valid:
            deny_codes.append(REASON_SESSION_INVALID)

        # Rule 8: allowance sufficient (only check when we have a number and
        # the order notional itself is computable).
        if (
            remaining_allowance is not None
            and REASON_AMOUNT_INVALID not in deny_codes
            and REASON_PRICE_INVALID not in deny_codes
        ):
            order_notional = notional if notional is not None else (
                float(intent.amount) * float(intent.price)
            )
            if order_notional > float(remaining_allowance):
                deny_codes.append(REASON_ALLOWANCE_INSUFFICIENT)

        if deny_codes:
            decision = _build_decision(
                DECISION_DENY,
                deny_codes,
                _empty_conditions(),
            )
            # When the failure is specifically a session issue and the caller
            # supplied a richer reason string, prefer it for readability while
            # keeping the deterministic code intact.
            if (
                session_reason
                and deny_codes == [REASON_SESSION_INVALID]
            ):
                decision["human_reason"] = session_reason
            return decision

        # No denials – build the ALLOW / ALLOW_WITH_CONDITIONS response. We
        # always surface the active limits as conditions so downstream systems
        # know what the order was approved under.
        conditions = _empty_conditions()
        if _rules.MAX_ORDER_NOTIONAL is not None:
            conditions["max_notional"] = float(_rules.MAX_ORDER_NOTIONAL)
        if intent.expires_at:
            conditions["valid_until"] = int(intent.expires_at)
        if _rules.ALLOWED_ASSETS:
            conditions["allowed_assets"] = sorted(_rules.ALLOWED_ASSETS)

        has_conditions = any(value is not None for value in conditions.values())
        decision_value = (
            DECISION_ALLOW_WITH_CONDITIONS if has_conditions else DECISION_ALLOW
        )
        return _build_decision(decision_value, [], conditions)
