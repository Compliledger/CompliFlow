"""In-memory store for issued proof bundles.

Proof bundles are keyed by their ``proof_hash``.  This is intentionally
process-local and dependency-free; it is sufficient for the verification
endpoints exposed today and can later be swapped for a persistent backend
without touching the routes that depend on the public functions below.
"""
from __future__ import annotations

import threading
from typing import Dict, Optional


_lock = threading.Lock()
_bundles: Dict[str, dict] = {}


def store_bundle(bundle: dict) -> None:
    """Persist ``bundle`` keyed by its ``proof_hash``.

    No-op when the bundle does not contain a ``proof_hash``.
    """
    proof_hash = bundle.get("proof_hash")
    if not proof_hash:
        return
    with _lock:
        _bundles[proof_hash] = bundle


def get_bundle(proof_hash: str) -> Optional[dict]:
    with _lock:
        return _bundles.get(proof_hash)


def clear() -> None:
    """Test helper — empties the store."""
    with _lock:
        _bundles.clear()
