from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ISSUE_PAYLOAD = {
    "wallet": "0xabc",
    "session_key": "test-session-key",
    "jurisdiction": "US",
    "assets": ["ytest.usd"],
    "max_notional": 10000,
}


def test_issue_credential():
    r = client.post("/v1/credential/issue", json=ISSUE_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    assert "credential" in data
    assert "credential_hash" in data
    assert "signature" in data
    assert "public_key" in data
    assert data["credential"]["wallet"] == "0xabc"
    assert data["credential"]["max_notional"] == 10000
    assert data["credential"]["remaining_notional"] == 10000
    assert "expires_at" in data["credential"]
    assert "nonce" in data["credential"]


def test_issue_credential_blocked_jurisdiction():
    payload = {**ISSUE_PAYLOAD, "jurisdiction": "BLOCKED_REGION"}
    r = client.post("/v1/credential/issue", json=payload)
    assert r.status_code == 403
    assert "reason" in r.json()["detail"]


def test_issue_credential_invalid_notional():
    payload = {**ISSUE_PAYLOAD, "max_notional": 0}
    r = client.post("/v1/credential/issue", json=payload)
    assert r.status_code == 403


def test_verify_credential_valid():
    r = client.post("/v1/credential/issue", json=ISSUE_PAYLOAD)
    assert r.status_code == 200
    bundle = r.json()

    r2 = client.post("/v1/credential/verify", json={"credential": bundle})
    assert r2.status_code == 200
    data = r2.json()
    assert data["valid"] is True
    assert data["checks"]["hash_match"] is True
    assert data["checks"]["signature_valid"] is True
    assert data["checks"]["not_expired"] is True


def test_verify_credential_tampered():
    r = client.post("/v1/credential/issue", json=ISSUE_PAYLOAD)
    assert r.status_code == 200
    bundle = r.json()

    # Tamper with the payload
    bundle["credential"]["wallet"] = "0xevil"

    r2 = client.post("/v1/credential/verify", json={"credential": bundle})
    assert r2.status_code == 200
    data = r2.json()
    assert data["valid"] is False
    assert data["checks"]["hash_match"] is False


def test_spend_credential():
    r = client.post("/v1/credential/issue", json=ISSUE_PAYLOAD)
    assert r.status_code == 200
    credential_hash = r.json()["credential_hash"]

    r2 = client.post(
        "/v1/credential/spend",
        json={"credential_hash": credential_hash, "notional": 1000, "intent_hash": "abc123"},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["ok"] is True
    assert data["remaining_notional"] == 9000


def test_spend_credential_multiple():
    r = client.post("/v1/credential/issue", json=ISSUE_PAYLOAD)
    assert r.status_code == 200
    credential_hash = r.json()["credential_hash"]

    client.post(
        "/v1/credential/spend",
        json={"credential_hash": credential_hash, "notional": 3000, "intent_hash": "h1"},
    )
    r2 = client.post(
        "/v1/credential/spend",
        json={"credential_hash": credential_hash, "notional": 2000, "intent_hash": "h2"},
    )
    assert r2.status_code == 200
    assert r2.json()["remaining_notional"] == 5000


def test_spend_insufficient_notional():
    r = client.post("/v1/credential/issue", json=ISSUE_PAYLOAD)
    assert r.status_code == 200
    credential_hash = r.json()["credential_hash"]

    r2 = client.post(
        "/v1/credential/spend",
        json={"credential_hash": credential_hash, "notional": 20000, "intent_hash": "abc"},
    )
    assert r2.status_code == 400


def test_spend_credential_not_found():
    r = client.post(
        "/v1/credential/spend",
        json={"credential_hash": "nonexistent", "notional": 100, "intent_hash": "abc"},
    )
    assert r.status_code == 404
