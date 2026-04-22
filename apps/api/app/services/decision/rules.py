"""Static rules configuration for the CompliFlow policy engine.

Kept intentionally simple and readable: a flat module of constants that the
:mod:`policy_engine` consumes. Override at runtime by mutating these values or
shadowing them in tests; no external config loader is required for the MVP.
"""

from __future__ import annotations

from typing import Optional

# Bumped whenever the rule set or decision schema changes in a meaningful way.
POLICY_VERSION: str = "2025-04-22.v2"

# Sides that the engine will accept.
VALID_SIDES: tuple[str, ...] = ("BUY", "SELL")

# Jurisdictions that are explicitly blocked. Compared case-sensitively against
# ``TradeIntent.jurisdiction``.
BLOCKED_JURISDICTIONS: frozenset[str] = frozenset({"BLOCKED_REGION"})

# Assets that the platform allows trading. ``None`` (or empty) disables the
# allowlist check entirely – useful for early MVP environments.
ALLOWED_ASSETS: Optional[frozenset[str]] = frozenset({
    "ytest.usd",
    "yusd",
    "yeth",
    "ybtc",
})

# Optional cap on the notional (amount * price) for a single order. Set to
# ``None`` to disable the check.
MAX_ORDER_NOTIONAL: Optional[float] = 1_000_000.0
