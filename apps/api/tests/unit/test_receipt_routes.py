"""Route-level tests for the proof-bundle receipt endpoints."""
import base64

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.proof import store as proof_store
from app.services.proof.receipt_signer import ReceiptSigner


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_store():
    proof_store.clear()
    yield
    proof_store.clear()


def _bundle(**overrides):
    kwargs = dict(
        decision={"decision": "ALLOW"},
        wallet="0xWallet",
        session_key="sk-1",
        intent={"a": 1},
        ttl_seconds=300,
    )
    kwargs.update(overrides)
    return ReceiptSigner.create_proof_bundle(**kwargs)


class TestVerifyEndpoint:
    def test_verify_valid_bundle(self, client):
        bundle = _bundle()
        r = client.post("/v1/receipt/verify", json=bundle)
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True
        assert body["proof_hash"] == bundle["proof_hash"]
        assert body["expires_at"] == bundle["expires_at"]

    def test_verify_tampered_bundle(self, client):
        bundle = _bundle()
        bundle["wallet"] = "0xEvil"
        r = client.post("/v1/receipt/verify", json=bundle)
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert body["reason"] == "proof_hash_mismatch"

    def test_verify_expired_bundle(self, client):
        bundle = _bundle(ttl_seconds=-5)
        r = client.post("/v1/receipt/verify", json=bundle)
        assert r.json()["reason"] == "expired"

    def test_verify_legacy_payload_shape(self, client):
        legacy = ReceiptSigner.sign({"hello": "world"})
        r = client.post(
            "/v1/receipt/verify",
            json={"payload": legacy["payload"], "signature": legacy["signature"]},
        )
        assert r.json()["valid"] is True

    def test_verify_legacy_bad_signature(self, client):
        r = client.post(
            "/v1/receipt/verify",
            json={"payload": {"x": 1}, "signature": base64.b64encode(b"\x00" * 64).decode()},
        )
        body = r.json()
        assert body["valid"] is False
        assert body["reason"] == "invalid_signature"

    def test_verify_unrecognized_shape(self, client):
        r = client.post("/v1/receipt/verify", json={})
        assert r.json()["reason"] == "unrecognized_receipt_shape"


class TestGetByProofHash:
    def test_get_returns_stored_bundle(self, client):
        bundle = _bundle()
        proof_store.store_bundle(bundle)
        r = client.get(f"/v1/receipt/{bundle['proof_hash']}")
        assert r.status_code == 200
        assert r.json()["proof_hash"] == bundle["proof_hash"]

    def test_get_unknown_returns_404(self, client):
        r = client.get("/v1/receipt/" + "0" * 64)
        assert r.status_code == 404
