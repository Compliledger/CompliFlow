"""Compatibility shim.

Moved to ``app.services.proof.receipt_signer``.
"""

from app.services.proof.receipt_signer import *  # noqa: F401,F403
from app.services.proof import receipt_signer as _impl

# Re-export common module-level attributes that are imported by name
try:
    from app.services.proof.receipt_signer import public_key  # noqa: F401
except ImportError:  # pragma: no cover - public_key may not always exist
    pass

__all__ = getattr(_impl, "__all__", [name for name in dir(_impl) if not name.startswith("_")])
