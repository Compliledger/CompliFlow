"""Settlement capability.

Validates settlement payloads and manages settlement status transitions
within CompliFlow's enforcement platform.

This module is a new scaffold introduced as part of the platform refactor.
It intentionally provides a small, dependency-free surface so callers can
begin integrating without any behavioural change to existing routes.
"""

from app.services.settlement.settlement_service import (
    SettlementService,
    SettlementStatus,
    SettlementValidationError,
)
from app.services.settlement.settlement_engine import (
    SettlementEngine,
    DECISION_ALLOW,
    DECISION_DENY,
    DECISION_ALLOW_WITH_CONDITIONS,
)

__all__ = [
    "SettlementService",
    "SettlementStatus",
    "SettlementValidationError",
    "SettlementEngine",
    "DECISION_ALLOW",
    "DECISION_DENY",
    "DECISION_ALLOW_WITH_CONDITIONS",
]
