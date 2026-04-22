"""Settlement service.

Provides validation primitives and a status state-machine for settlements.
This is a new capability scaffold introduced as part of the CompliFlow
enforcement-platform refactor. No existing route depends on it yet; it is
safe to extend without affecting the current deployment path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Optional

logger = logging.getLogger(__name__)


class SettlementStatus(str, Enum):
    """Lifecycle states a settlement can be in."""

    PENDING = "pending"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    SETTLED = "settled"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Allowed forward transitions. Anything not listed is rejected.
_ALLOWED_TRANSITIONS: Dict[SettlementStatus, frozenset] = {
    SettlementStatus.PENDING: frozenset(
        {SettlementStatus.VALIDATED, SettlementStatus.FAILED, SettlementStatus.CANCELLED}
    ),
    SettlementStatus.VALIDATED: frozenset(
        {SettlementStatus.SUBMITTED, SettlementStatus.FAILED, SettlementStatus.CANCELLED}
    ),
    SettlementStatus.SUBMITTED: frozenset(
        {SettlementStatus.SETTLED, SettlementStatus.FAILED}
    ),
    SettlementStatus.SETTLED: frozenset(),
    SettlementStatus.FAILED: frozenset(),
    SettlementStatus.CANCELLED: frozenset(),
}


class SettlementValidationError(ValueError):
    """Raised when a settlement payload fails validation."""


@dataclass
class SettlementResult:
    ok: bool
    status: SettlementStatus
    errors: list = field(default_factory=list)


class SettlementService:
    """Validate settlement payloads and govern status transitions."""

    REQUIRED_FIELDS: Iterable[str] = ("settlement_id", "wallet", "amount", "asset")

    @classmethod
    def validate(cls, payload: Optional[Dict[str, Any]]) -> SettlementResult:
        """Validate a settlement payload.

        Returns a :class:`SettlementResult`. Does not raise; callers that
        prefer exception-based flow can use :meth:`validate_or_raise`.
        """
        errors: list = []
        if not isinstance(payload, dict):
            errors.append("payload must be a mapping")
            return SettlementResult(ok=False, status=SettlementStatus.FAILED, errors=errors)

        for field_name in cls.REQUIRED_FIELDS:
            if field_name not in payload or payload[field_name] in (None, ""):
                errors.append(f"missing required field: {field_name}")

        amount = payload.get("amount")
        if amount is not None:
            try:
                if float(amount) <= 0:
                    errors.append("amount must be > 0")
            except (TypeError, ValueError):
                errors.append("amount must be numeric")

        if errors:
            return SettlementResult(ok=False, status=SettlementStatus.FAILED, errors=errors)
        return SettlementResult(ok=True, status=SettlementStatus.VALIDATED)

    @classmethod
    def validate_or_raise(cls, payload: Optional[Dict[str, Any]]) -> SettlementResult:
        result = cls.validate(payload)
        if not result.ok:
            raise SettlementValidationError("; ".join(result.errors))
        return result

    @staticmethod
    def can_transition(current: SettlementStatus, target: SettlementStatus) -> bool:
        """Return True when ``current -> target`` is a permitted transition."""
        return target in _ALLOWED_TRANSITIONS.get(current, frozenset())

    @classmethod
    def transition(
        cls, current: SettlementStatus, target: SettlementStatus
    ) -> SettlementStatus:
        """Apply a status transition or raise :class:`ValueError`."""
        if not cls.can_transition(current, target):
            raise ValueError(
                f"illegal settlement transition: {current.value} -> {target.value}"
            )
        logger.info("settlement transition %s -> %s", current.value, target.value)
        return target
