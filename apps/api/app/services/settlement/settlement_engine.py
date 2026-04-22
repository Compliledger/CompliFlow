"""CompliFlow settlement enforcement engine.

Produces structured, auditable decisions for whether a matched trade is
allowed to settle. Mirrors the shape of the intent ``PolicyEngine`` so that
downstream systems (audit log, UI, evidence storage) can consume both
decision streams uniformly.

Decision shape::

    {
        "decision": "ALLOW" | "DENY" | "ALLOW_WITH_CONDITIONS",
        "reason_codes": ["..."],
        "human_reason": "string",
        "conditions": {
            "valid_until": int | None,           # unix timestamp (seconds)
        },
        "policy_version": "string",
        "settlement_context": {
            "order_id": "string",
            "match_id": "string | null",
            "proof_hash": "string | null",
        },
    }

This module is intentionally a *validation and evidence layer only* — it
does not perform any blockchain settlement, transfer of funds, or external
state mutation.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature

from app.services.decision import rules as _rules
from app.services.proof.receipt_signer import public_key as _receipt_public_key

logger = logging.getLogger(__name__)

__all__ = [
    "SettlementEngine",
    "DECISION_ALLOW",
    "DECISION_DENY",
    "DECISION_ALLOW_WITH_CONDITIONS",
    "ELIGIBLE_EXECUTION_STATUSES",
    "VALID_EXECUTION_STATUSES",
]

DECISION_ALLOW = "ALLOW"
DECISION_DENY = "DENY"
DECISION_ALLOW_WITH_CONDITIONS = "ALLOW_WITH_CONDITIONS"

# Execution lifecycle values understood by the settlement engine. The set is
# intentionally narrow for the MVP and matches the values surfaced by the
# Yellow integration today.
VALID_EXECUTION_STATUSES: frozenset[str] = frozenset(
    {"SUBMITTED", "MATCHED", "ESCROW_LOCKED", "SETTLED"}
)

# Statuses from which a settlement may legitimately proceed. ``SUBMITTED``
# is too early (no match yet) and ``SETTLED`` is already terminal.
ELIGIBLE_EXECUTION_STATUSES: frozenset[str] = frozenset(
    {"MATCHED", "ESCROW_LOCKED"}
)

# Deterministic, machine-readable reason codes.
REASON_RECEIPT_MISSING = "RECEIPT_MISSING"
REASON_RECEIPT_INVALID = "RECEIPT_INVALID"
REASON_EXECUTION_STATUS_INVALID = "EXECUTION_STATUS_INVALID"
REASON_EXECUTION_STATUS_NOT_ELIGIBLE = "EXECUTION_STATUS_NOT_ELIGIBLE"
REASON_JURISDICTION_BLOCKED = "JURISDICTION_BLOCKED"
REASON_INTENT_EXPIRED = "INTENT_EXPIRED"
REASON_COLLATERAL_INSUFFICIENT = "COLLATERAL_INSUFFICIENT"
REASON_ORDER_ID_MISSING = "ORDER_ID_MISSING"

_REASON_TEXT: Dict[str, str] = {
    REASON_RECEIPT_MISSING: "Receipt is missing.",
    REASON_RECEIPT_INVALID: "Receipt signature could not be verified.",
    REASON_EXECUTION_STATUS_INVALID: (
        "Execution status is not a recognised settlement-lifecycle value."
    ),
    REASON_EXECUTION_STATUS_NOT_ELIGIBLE: (
        "Execution status is not eligible for settlement."
    ),
    REASON_JURISDICTION_BLOCKED: "Jurisdiction is blocked by policy.",
    REASON_INTENT_EXPIRED: "Intent has expired and can no longer settle.",
    REASON_COLLATERAL_INSUFFICIENT: "Collateral check did not pass.",
    REASON_ORDER_ID_MISSING: "order_id is required.",
}


def _empty_conditions() -> Dict[str, Any]:
    return {"valid_until": None}


def _settlement_context(
    order_id: Optional[str],
    match_id: Optional[str],
    proof_hash: Optional[str],
) -> Dict[str, Any]:
    return {
        "order_id": order_id or "",
        "match_id": match_id,
        "proof_hash": proof_hash,
    }


def _build_decision(
    decision: str,
    reason_codes: list[str],
    conditions: Dict[str, Any],
    settlement_context: Dict[str, Any],
    extra_human_reason: Optional[str] = None,
) -> Dict[str, Any]:
    if reason_codes:
        human = "; ".join(_REASON_TEXT.get(code, code) for code in reason_codes)
    elif extra_human_reason:
        human = extra_human_reason
    else:
        human = "Settlement allowed."

    return {
        "decision": decision,
        "reason_codes": list(reason_codes),
        "human_reason": human,
        "conditions": conditions,
        "policy_version": _rules.POLICY_VERSION,
        "settlement_context": settlement_context,
    }


# Internal error tags returned from :func:`_verify_receipt`. Kept as
# constants so the call-site can reliably translate them into reason codes.
_RECEIPT_ERR_MISSING = "missing"
_RECEIPT_ERR_MISSING_FIELDS = "missing_payload_or_signature"
_RECEIPT_ERR_INVALID_SIGNATURE = "invalid_signature"
_RECEIPT_ERR_VERIFICATION = "verification_error"

# Error tags that should map to ``RECEIPT_MISSING`` (vs. ``RECEIPT_INVALID``).
_RECEIPT_MISSING_ERRORS = frozenset(
    {_RECEIPT_ERR_MISSING, _RECEIPT_ERR_MISSING_FIELDS}
)


def _verify_receipt(receipt: Optional[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
    """Best-effort verification of a signed receipt.

    Returns ``(is_valid, error_tag)``. ``error_tag`` is ``None`` on success
    and otherwise one of the ``_RECEIPT_ERR_*`` constants.
    """
    if not isinstance(receipt, dict) or not receipt:
        return False, _RECEIPT_ERR_MISSING

    payload = receipt.get("payload")
    signature = receipt.get("signature")
    if payload is None or not signature:
        return False, _RECEIPT_ERR_MISSING_FIELDS

    try:
        signature_bytes = base64.b64decode(signature)
        message = json.dumps(payload, sort_keys=True).encode()
        _receipt_public_key.verify(signature_bytes, message)
        return True, None
    except InvalidSignature:
        return False, _RECEIPT_ERR_INVALID_SIGNATURE
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Receipt verification raised unexpected error: %s", exc)
        return False, _RECEIPT_ERR_VERIFICATION


def _compute_proof_hash(proofs: Optional[Dict[str, Any]]) -> Optional[str]:
    if not proofs:
        return None
    try:
        canonical = json.dumps(proofs, sort_keys=True, default=str).encode()
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(canonical).hexdigest()


class SettlementEngine:
    """Stateless evaluator that decides whether a match may settle."""

    @staticmethod
    def evaluate(
        *,
        order_id: Optional[str],
        intent: Optional[Dict[str, Any]],
        receipt: Optional[Dict[str, Any]],
        execution_status: Optional[str],
        proofs: Optional[Dict[str, Any]] = None,
        now: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Evaluate a settlement request and return a structured decision."""

        intent = intent or {}
        proofs = proofs or {}
        now_ts = int(now if now is not None else time.time())

        # Derive evidence pointers up-front so they appear on every response,
        # including denials (useful for audit / debugging).
        match_id = proofs.get("match_id") if isinstance(proofs, dict) else None
        proof_hash = (
            proofs.get("proof_hash")
            if isinstance(proofs, dict) and proofs.get("proof_hash")
            else _compute_proof_hash(proofs)
        )
        ctx = _settlement_context(order_id, match_id, proof_hash)

        deny_codes: list[str] = []

        # Rule 0: order_id must be present so audit/evidence is anchored.
        if not order_id:
            deny_codes.append(REASON_ORDER_ID_MISSING)

        # Rule 1 & 2: receipt exists and verifies.
        receipt_ok, receipt_error = _verify_receipt(receipt)
        if not receipt_ok:
            if receipt_error in _RECEIPT_MISSING_ERRORS:
                deny_codes.append(REASON_RECEIPT_MISSING)
            else:
                deny_codes.append(REASON_RECEIPT_INVALID)

        # Rule 3: execution status is eligible.
        if execution_status not in VALID_EXECUTION_STATUSES:
            deny_codes.append(REASON_EXECUTION_STATUS_INVALID)
        elif execution_status not in ELIGIBLE_EXECUTION_STATUSES:
            deny_codes.append(REASON_EXECUTION_STATUS_NOT_ELIGIBLE)

        # Rule 4: jurisdiction not blocked.
        jurisdiction = intent.get("jurisdiction")
        if jurisdiction and jurisdiction in _rules.BLOCKED_JURISDICTIONS:
            deny_codes.append(REASON_JURISDICTION_BLOCKED)

        # Rule 5: intent has not expired.
        expires_at = intent.get("expires_at")
        try:
            expires_at_int = int(expires_at) if expires_at is not None else None
        except (TypeError, ValueError):
            expires_at_int = None
        if expires_at_int is not None and expires_at_int < now_ts:
            deny_codes.append(REASON_INTENT_EXPIRED)

        # Rule 6: optional collateral_ok flag (only checked when present).
        if isinstance(proofs, dict) and "collateral_ok" in proofs:
            if not bool(proofs.get("collateral_ok")):
                deny_codes.append(REASON_COLLATERAL_INSUFFICIENT)

        if deny_codes:
            return _build_decision(
                DECISION_DENY,
                deny_codes,
                _empty_conditions(),
                ctx,
            )

        # No denials – build ALLOW / ALLOW_WITH_CONDITIONS. We surface the
        # intent's own expiry as the settlement validity window so callers
        # can cache the decision safely.
        conditions = _empty_conditions()
        if expires_at_int is not None:
            conditions["valid_until"] = expires_at_int

        has_conditions = any(value is not None for value in conditions.values())
        decision_value = (
            DECISION_ALLOW_WITH_CONDITIONS if has_conditions else DECISION_ALLOW
        )
        return _build_decision(decision_value, [], conditions, ctx)
