"""Compatibility shim.

Moved to ``app.services.session.session_service``.
"""

from app.services.session.session_service import *  # noqa: F401,F403
from app.services.session import session_service as _impl
from app.services.session.session_service import SessionService  # noqa: F401

__all__ = getattr(_impl, "__all__", [name for name in dir(_impl) if not name.startswith("_")])
