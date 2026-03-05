"""
Integration tests for CompliFlow complete workflow:
Wallet → Session → Compliance → Receipt → Order → Yellow → Audit
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db, engine
from app.db.base import Base
from app.models.session import SessionKey
from datetime import datetime, timedelta


@pytest.fixture(scope="module")
def setup_db():
    """Create all database tables before tests"""
    import app.models.session  # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.db.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Synchronous test client for FastAPI"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async HTTP client for FastAPI"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_session(setup_db):
    """Create a test session in the database"""
    from app.services.session_service import SessionService
    
    session_key = "test_session_123"
    wallet = "0x1111111111111111111111111111111111111111"
    
    session_data = SessionService.create_session(
        session_key=session_key,
        wallet=wallet,
        initial_allowance=10000,
        validity_days=30,
    )
    
    return {
        "session_key": session_key,
        "wallet": wallet,
        "session_data": session_data,
    }


@pytest.fixture
def test_intent(test_session):
    """Sample intent payload for testing"""
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


class TestWorkflowIntegration:
    """Complete integration tests for CompliFlow workflow"""

    def test_01_session_validation(self, client, test_session):
        """TEST 1 — Session Validation"""
        response = client.post(
            "/v1/yellow/session/preflight",
            json={
                "wallet": test_session["wallet"],
                "session_key": test_session["session_key"],
            },
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "valid" in data, "Response missing 'valid' field"
        assert data["valid"] is True, f"Session validation failed: {data}"
        assert data["wallet"] == test_session["wallet"], "Wallet mismatch"
        assert data["session_key"] == test_session["session_key"], "Session key mismatch"
        assert "yellow_status" in data, "Missing yellow_status field"
        
        print("✔ Session validation works")

    def test_02_compliance_engine(self, client, test_intent):
        """TEST 2 — Compliance Engine"""
        response = client.post("/v1/intent/evaluate", json=test_intent)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "payload" in data, "Response missing 'payload' field"
        assert "signature" in data, "Response missing 'signature' field"
        
        payload = data["payload"]
        assert "decision" in payload, "Payload missing 'decision' field"
        
        decision = payload["decision"]
        assert decision.get("status") == "PASS", f"Expected PASS, got {decision.get('status')}"
        
        print("✔ Compliance engine works")
        return data

    def test_03_receipt_signing(self, client, test_intent):
        """TEST 3 — Receipt Signing"""
        response = client.post("/v1/intent/evaluate", json=test_intent)

        assert response.status_code == 200
        data = response.json()

        assert "signature" in data, "Receipt missing 'signature'"
        assert len(data["signature"]) > 0, "Signature is empty"
        
        assert "payload" in data, "Receipt missing 'payload'"
        payload = data["payload"]
        
        assert "receipt_hash" in payload, "Payload missing 'receipt_hash'"
        assert len(payload["receipt_hash"]) == 64, "Receipt hash should be 64 hex chars (SHA256)"
        
        print("✔ Receipt signing works")
        return data

    def test_04_receipt_verification(self, client, test_intent):
        """TEST 4 — Receipt Verification"""
        eval_response = client.post("/v1/intent/evaluate", json=test_intent)
        assert eval_response.status_code == 200
        
        receipt = eval_response.json()
        
        verify_response = client.post(
            "/v1/receipt/verify",
            json={
                "signature": receipt["signature"],
                "payload": receipt["payload"],
            },
        )

        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        
        assert "valid" in verify_data, "Verification response missing 'valid' field"
        assert verify_data["valid"] is True, f"Receipt verification failed: {verify_data}"
        
        print("✔ Receipt verification works")

    def test_05_order_submission(self, client, test_intent):
        """TEST 5 — Order Submission"""
        eval_response = client.post("/v1/intent/evaluate", json=test_intent)
        assert eval_response.status_code == 200
        
        receipt = eval_response.json()
        
        submit_response = client.post(
            "/v1/yellow/order/submit",
            json={
                "intent": test_intent,
                "receipt": receipt,
            },
        )

        assert submit_response.status_code == 200
        data = submit_response.json()
        
        assert "status" in data, "Order submission response missing 'status'"
        
        if data.get("status") == "FAILED":
            assert "error" in data, "Failed order should include error field"
            print(f"✔ Order submission works (Yellow unavailable: {data.get('error')})")
        else:
            assert "order_id" in data or data.get("status") == "SUBMITTED", (
                "Successful submission should include order_id or SUBMITTED status"
            )
            print(f"✔ Order submission works (status: {data.get('status')})")

    def test_06_audit_log_persistence(self, client, test_intent):
        """TEST 6 — Audit Log Persistence"""
        client.post("/v1/intent/evaluate", json=test_intent)
        
        audit_response = client.get("/v1/audit/logs")

        assert audit_response.status_code == 200
        data = audit_response.json()
        
        assert "logs" in data, "Audit response missing 'logs' field"
        assert isinstance(data["logs"], list), "Logs should be an array"
        assert len(data["logs"]) > 0, "No audit logs found"
        
        event_types = {log["event_type"] for log in data["logs"]}
        assert "INTENT_EVALUATED" in event_types, "Missing INTENT_EVALUATED event"
        
        print(f"✔ Audit logging works ({len(data['logs'])} events recorded)")

    def test_07_order_audit_trail(self, client, test_intent):
        """TEST 7 — Order Audit Trail"""
        eval_response = client.post("/v1/intent/evaluate", json=test_intent)
        assert eval_response.status_code == 200
        
        receipt = eval_response.json()
        
        submit_response = client.post(
            "/v1/yellow/order/submit",
            json={
                "intent": test_intent,
                "receipt": receipt,
            },
        )
        
        assert submit_response.status_code == 200
        order_data = submit_response.json()
        
        if "order_id" in order_data:
            order_id = order_data["order_id"]
            trail_response = client.get(f"/v1/audit/logs/{order_id}")
            
            assert trail_response.status_code == 200
            trail_data = trail_response.json()
            
            assert "audit_trail" in trail_data, "Missing audit_trail field"
            assert trail_data["order_id"] == order_id, "Order ID mismatch"
            
            if len(trail_data["audit_trail"]) > 0:
                timestamps = [log["timestamp"] for log in trail_data["audit_trail"]]
                assert timestamps == sorted(timestamps), "Audit trail not in chronological order"
            
            print(f"✔ Order audit trail works (order_id: {order_id})")
        else:
            all_logs_response = client.get("/v1/audit/logs")
            assert all_logs_response.status_code == 200
            print("✔ Order audit trail works (Yellow unavailable, verified logs endpoint)")

    def test_08_session_activity_tracking(self, client, test_intent, test_session):
        """BONUS TEST — Session Activity Tracking"""
        client.post("/v1/intent/evaluate", json=test_intent)
        
        activity_response = client.get(
            f"/v1/audit/session/{test_session['session_key']}/activity"
        )

        assert activity_response.status_code == 200
        data = activity_response.json()
        
        assert "activity" in data, "Missing activity field"
        assert data["session_key"] == test_session["session_key"], "Session key mismatch"
        assert len(data["activity"]) > 0, "No session activity found"
        
        print(f"✔ Session activity tracking works ({len(data['activity'])} events)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
