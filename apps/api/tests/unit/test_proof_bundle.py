"""Unit tests for the proof-bundle helpers."""
import base64
import copy
import time

import pytest

from app.services.proof.receipt_signer import (
    ReceiptSigner,
    canonicalize,
    hash_object,
    sha256_hex,
)
from app.services.proof import store as proof_store


@pytest.fixture(autouse=True)
def _clear_store():
    proof_store.clear()
    yield
    proof_store.clear()


def _make_bundle(**overrides):
    kwargs = dict(
        decision={"decision": "ALLOW", "reason_codes": ["OK"]},
        wallet="0xWalletAddress",
        session_key="session-key-xyz",
        intent={"asset": "USDC", "amount": 100, "price": 1.0, "side": "BUY"},
        ttl_seconds=300,
    )
    kwargs.update(overrides)
    return ReceiptSigner.create_proof_bundle(**kwargs)


class TestCanonicalization:
    def test_key_order_independent(self):
        a = {"b": 1, "a": [1, 2, {"y": 2, "x": 1}]}
        b = {"a": [1, 2, {"x": 1, "y": 2}], "b": 1}
        assert canonicalize(a) == canonicalize(b)

    def test_no_whitespace(self):
        assert b" " not in canonicalize({"a": 1, "b": 2})

    def test_hash_object_is_hex_sha256(self):
        h = hash_object({"x": 1})
        assert len(h) == 64
        int(h, 16)  # valid hex


class TestProofBundleShape:
    def test_required_fields_present(self):
        bundle = _make_bundle()
        for key in (
            "proof_version", "issued_at", "expires_at", "intent_hash",
            "decision_hash", "proof_hash", "wallet", "session_key_hash",
            "decision", "signature", "public_key",
        ):
            assert key in bundle, key

    def test_proof_version_default(self):
        assert _make_bundle()["proof_version"] == "1.0"

    def test_session_key_is_hashed_not_revealed(self):
        bundle = _make_bundle(session_key="super-secret")
        assert "super-secret" not in str(bundle)
        assert bundle["session_key_hash"] == sha256_hex(b"super-secret")

    def test_expiry_uses_ttl(self):
        bundle = _make_bundle(ttl_seconds=60)
        assert bundle["expires_at"] - bundle["issued_at"] == 60

    def test_proof_hash_excludes_signature_and_public_key(self):
        bundle = _make_bundle()
        recomputed = ReceiptSigner._recompute_proof_hash(bundle)
        assert recomputed == bundle["proof_hash"]


class TestVerify:
    def test_valid_bundle(self):
        ok, reason = ReceiptSigner.verify_bundle(_make_bundle())
        assert ok and reason is None

    def test_tampered_decision_detected(self):
        bundle = _make_bundle()
        bundle["decision"]["reason_codes"] = ["EVIL"]
        ok, reason = ReceiptSigner.verify_bundle(bundle)
        assert not ok and reason == "proof_hash_mismatch"

    def test_tampered_wallet_detected(self):
        bundle = _make_bundle()
        bundle["wallet"] = "0xEvil"
        ok, reason = ReceiptSigner.verify_bundle(bundle)
        assert not ok and reason == "proof_hash_mismatch"

    def test_invalid_signature_detected(self):
        bundle = _make_bundle()
        bundle["signature"] = base64.b64encode(b"\x00" * 64).decode()
        ok, reason = ReceiptSigner.verify_bundle(bundle)
        assert not ok and reason == "invalid_signature"

    def test_expired_bundle_detected(self):
        bundle = _make_bundle(ttl_seconds=-10)
        ok, reason = ReceiptSigner.verify_bundle(bundle)
        assert not ok and reason == "expired"

    def test_missing_field_detected(self):
        bundle = _make_bundle()
        bundle.pop("public_key")
        ok, reason = ReceiptSigner.verify_bundle(bundle)
        assert not ok and reason.startswith("missing_field")


class TestStore:
    def test_store_and_get(self):
        bundle = _make_bundle()
        proof_store.store_bundle(bundle)
        assert proof_store.get_bundle(bundle["proof_hash"]) == bundle

    def test_get_unknown_returns_none(self):
        assert proof_store.get_bundle("does-not-exist") is None


class TestSettlementProofGenerality:
    """The bundle format must be reusable for non-execution proofs."""

    def test_settlement_validation_proof_roundtrip(self):
        decision = {
            "decision": "SETTLED",
            "settlement_id": "stl_42",
            "amount": "1000.00",
            "asset": "USDC",
        }
        bundle = ReceiptSigner.create_proof_bundle(
            decision=decision,
            wallet="0xParty",
            session_key="settle-session",
            intent=None,
        )
        ok, reason = ReceiptSigner.verify_bundle(bundle)
        assert ok, reason
        assert bundle["decision"]["settlement_id"] == "stl_42"
