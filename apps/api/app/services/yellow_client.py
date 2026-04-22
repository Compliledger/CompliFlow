"""Compatibility shim.

Moved to ``app.services.execution.yellow_client``. Re-exported for legacy
imports during the enforcement-platform refactor.
"""

from app.services.execution.yellow_client import *  # noqa: F401,F403
from app.services.execution import yellow_client as _impl
from app.services.execution.yellow_client import yellow_client  # noqa: F401

__all__ = getattr(_impl, "__all__", [name for name in dir(_impl) if not name.startswith("_")])
