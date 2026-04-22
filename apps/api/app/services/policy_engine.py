"""Compatibility shim.

The policy engine moved to ``app.services.decision.policy_engine`` as part of
the CompliFlow enforcement-platform refactor. This module re-exports the
public API so legacy imports continue to work.
"""

from app.services.decision.policy_engine import *  # noqa: F401,F403
from app.services.decision import policy_engine as _impl

__all__ = getattr(_impl, "__all__", [name for name in dir(_impl) if not name.startswith("_")])
