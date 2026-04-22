"""Shared fixtures for the CompliFlow lifecycle test suite.

The fixtures here keep tests deterministic by:
  * pointing the SQLAlchemy engine at an isolated, per-test SQLite file,
  * generating unique session keys / wallets per test so suites can run in
    any order without leaking state, and
  * mocking the Yellow Network client so no network I/O occurs.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# Database isolation
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_db(monkeypatch):
    """Swap the global SQLAlchemy engine for a fresh per-test SQLite file.

    Mutates ``app.db.session.engine`` and ``SessionLocal`` so every module
    that imports them through ``get_db`` transparently uses the temp DB.
    All app tables are created up-front and torn down at the end of the
    test.
    """
    from app.db import session as db_session
    from app.db.base import Base
    import app.models.session  # noqa: F401 — registers SessionKey
    import app.models.audit_log  # noqa: F401 — registers AuditLog
    import app.db.models  # noqa: F401 — registers Intent / Receipt

    fd, path = tempfile.mkstemp(prefix="compliflow_test_", suffix=".db")
    os.close(fd)
    test_engine = create_engine(f"sqlite:///{path}")
    test_sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(db_session, "engine", test_engine)
    monkeypatch.setattr(db_session, "SessionLocal", test_sessionmaker)

    Base.metadata.create_all(bind=test_engine)
    try:
        yield test_engine
    finally:
        test_engine.dispose()
        try:
            os.unlink(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


@pytest.fixture()
def session_factory(isolated_db):
    """Return a callable that creates and persists a fresh session row."""
    from app.services.session_service import SessionService

    def _create(initial_allowance: float = 10000.0, validity_days: int = 30) -> Dict[str, Any]:
        session_key = f"sess_{_unique_suffix()}"
        wallet = f"0x{_unique_suffix():0>40}"
        SessionService.create_session(
            session_key=session_key,
            wallet=wallet,
            initial_allowance=initial_allowance,
            validity_days=validity_days,
        )
        return {"session_key": session_key, "wallet": wallet}

    return _create


@pytest.fixture()
def test_session(session_factory):
    return session_factory()


@pytest.fixture()
def test_intent(test_session) -> Dict[str, Any]:
    """A canonical, ALLOW-eligible TradeIntent payload."""
    return {
        "session_key": test_session["session_key"],
        "user_wallet": test_session["wallet"],
        "side": "BUY",
        "asset": "ytest.usd",
        "amount": 100,
        "price": 1.0,
        "jurisdiction": "ALLOWED",
        "expires_at": int((datetime.utcnow() + timedelta(minutes=30)).timestamp()),
    }


# ---------------------------------------------------------------------------
# Proof bundle helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_proof_bundle():
    """Build a valid proof bundle for a given intent + decision."""
    from app.services.proof.receipt_signer import ReceiptSigner

    def _build(intent: Dict[str, Any], decision: Dict[str, Any] | None = None,
               ttl_seconds: int = 300) -> Dict[str, Any]:
        decision = decision or {
            "decision": "ALLOW",
            "reason_codes": [],
            "human_reason": "Order allowed.",
            "policy_version": "test.v1",
            "conditions": {},
        }
        return ReceiptSigner.create_proof_bundle(
            decision=decision,
            wallet=intent["user_wallet"],
            session_key=intent["session_key"],
            intent=intent,
            ttl_seconds=ttl_seconds,
        )

    return _build


# ---------------------------------------------------------------------------
# Yellow client mocking
# ---------------------------------------------------------------------------

class FakeYellowClient:
    """Minimal in-memory stand-in for the Yellow Network client.

    Tracks the lifecycle of a submitted order so tests can assert on
    transitions without a real WebSocket.
    """

    def __init__(self, *, available: bool = True):
        self.available = available
        self.submitted_orders: list[dict] = []
        self.next_status: str = "SUBMITTED"
        self._statuses: Dict[str, str] = {}

    async def validate_session(self, session_key: str, wallet: str) -> Dict[str, Any]:
        if not self.available:
            return {
                "valid": False,
                "error": "yellow_network_unavailable",
                "mode": "error",
                "message": "Yellow unavailable",
            }
        return {
            "valid": True,
            "session_key": session_key,
            "wallet": wallet,
            "expires_at": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "allowance_remaining": 9999,
        }

    async def submit_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available:
            return {
                "error": "yellow_network_unavailable",
                "status": "FAILED",
                "mode": "error",
                "message": "Yellow unavailable",
            }
        order_id = f"order_{_unique_suffix()}"
        self.submitted_orders.append({"order_id": order_id, **order_data})
        self._statuses[order_id] = self.next_status
        return {
            "order_id": order_id,
            "status": self.next_status,
            "channel_status": "ACTIVE",
            "intent": order_data.get("intent"),
            "receipt": order_data.get("receipt"),
        }

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if order_id not in self._statuses:
            return {"error": "not_found", "status": "UNKNOWN", "mode": "error"}
        return {
            "order_id": order_id,
            "status": self._statuses[order_id],
            "channel_state": "ACTIVE",
        }

    def advance(self, order_id: str, new_status: str) -> None:
        self._statuses[order_id] = new_status

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok" if self.available else "unavailable"}

    async def get_market_data(self, asset_pair=None) -> Dict[str, Any]:
        return {"pair": asset_pair or "ytest.usd", "status": "not_supported"}


@pytest.fixture()
def fake_yellow():
    """Provide a FakeYellowClient and patch every reference to the singleton."""
    fake = FakeYellowClient(available=True)
    with patch("app.routes.yellow.yellow_client", fake):
        yield fake


@pytest.fixture()
def fake_yellow_unavailable():
    fake = FakeYellowClient(available=False)
    with patch("app.routes.yellow.yellow_client", fake):
        yield fake


# ---------------------------------------------------------------------------
# FastAPI client
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(isolated_db) -> TestClient:
    """TestClient bound to a fully-isolated DB for the test."""
    from app.main import app
    return TestClient(app)


# Ensure pytest-asyncio is not required: every async helper is awaited via
# ``asyncio.get_event_loop().run_until_complete`` if needed.
@pytest.fixture()
def run_async():
    def _run(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return _run
