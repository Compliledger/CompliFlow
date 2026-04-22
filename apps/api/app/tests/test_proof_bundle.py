"""Tests for proof bundle generation, verification, and tamper-detection."""

from __future__ import annotations

import base64
import copy

import pytest

from app.services.proof.receipt_signer import (
    ReceiptSigner,
    canonicalize,
    sha256_hex,
)

@pytest.fixture()
def sample_decision() -> dict:
    return {
        "decision": "ALLOW",
        "reason_codes": [],
        "human_reason": "Order allowed.",
        "policy_version": "test.v1",
        "conditions": {"max_notional": 1000.0},
    }


@pytest.fixture()
def sample_intent() -> dict:
    return {
        "session_key": "sess_proof",
        "user_wallet": "0x" + "b" * 40,
        "side": "BUY",
        "asset": "ytest.usd",
        "amount": 100,
        "price": 1.0,
    }


def _make_bundle(intent, decision, **overrides) -> dict:
    kwargs = dict(
        decision=decision,
        wallet=intent["user_wallet"],
        session_key=intent["session_key"],
        intent=intent,
        ttl_seconds=300,
    )
    kwargs.update(overrides)
    return ReceiptSigner.create_proof_bundle(**kwargs)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def test_bundle_contains_all_required_fields(sample_intent, sample_decision):
    bundle = _make_bundle(sample_intent, sample_decision)
    for key in (
        "proof_version",
        "issued_at",
        "expires_at",
        "intent_hash",
        "decision_hash",
        "proof_hash",
        "wallet",
        "session_key_hash",
        "decision",
        "signature",
        "public_key",
    ):
        assert key in bundle, f"missing field: {key}"


def test_bundle_does_not_leak_session_key(sample_intent, sample_decision):
    bundle = _make_bundle(
        {**sample_intent, "session_key": "super-secret"},
        sample_decision,
    )
    assert "super-secret" not in str(bundle)
    assert bundle["session_key_hash"] == sha256_hex(b"super-secret")


def test_proof_hash_is_deterministic(sample_intent, sample_decision):
    bundle = _make_bundle(sample_intent, sample_decision)
    core = {k: v for k, v in bundle.items()
            if k not in ("signature", "public_key", "proof_hash")}
    assert sha256_hex(canonicalize(core)) == bundle["proof_hash"]


# ---------------------------------------------------------------------------
# Verification: happy path
# ---------------------------------------------------------------------------

def test_verify_returns_ok_for_fresh_bundle(sample_intent, sample_decision):
    ok, reason = ReceiptSigner.verify_bundle(_make_bundle(sample_intent, sample_decision))
    assert ok is True
    assert reason is None


def test_verify_settlement_proof_roundtrip():
    """Bundle format must work for non-execution decisions too."""
    decision = {"decision": "SETTLED", "settlement_id": "stl_1"}
    bundle = ReceiptSigner.create_proof_bundle(
        decision=decision,
        wallet="0xparty",
        session_key="settle-sess",
        intent=None,
    )
    ok, reason = ReceiptSigner.verify_bundle(bundle)
    assert ok, reason


# ---------------------------------------------------------------------------
# Verification: tamper detection
# ---------------------------------------------------------------------------

def test_tampered_decision_payload_is_detected(sample_intent, sample_decision):
    bundle = _make_bundle(sample_intent, sample_decision)
    tampered = copy.deepcopy(bundle)
    tampered["decision"]["reason_codes"] = ["INJECTED"]

    ok, reason = ReceiptSigner.verify_bundle(tampered)
    assert ok is False
    assert reason == "proof_hash_mismatch"


def test_tampered_wallet_is_detected(sample_intent, sample_decision):
    bundle = _make_bundle(sample_intent, sample_decision)
    bundle["wallet"] = "0xattacker"
    ok, reason = ReceiptSigner.verify_bundle(bundle)
    assert ok is False
    assert reason == "proof_hash_mismatch"


def test_replaced_signature_is_detected(sample_intent, sample_decision):
    bundle = _make_bundle(sample_intent, sample_decision)
    bundle["signature"] = base64.b64encode(b"\x00" * 64).decode()
    ok, reason = ReceiptSigner.verify_bundle(bundle)
    assert ok is False
    assert reason == "invalid_signature"


def test_expired_bundle_is_detected(sample_intent, sample_decision):
    bundle = _make_bundle(sample_intent, sample_decision, ttl_seconds=-30)
    ok, reason = ReceiptSigner.verify_bundle(bundle)
    assert ok is False
    assert reason == "expired"


def test_missing_field_is_detected(sample_intent, sample_decision):
    bundle = _make_bundle(sample_intent, sample_decision)
    bundle.pop("public_key")
    ok, reason = ReceiptSigner.verify_bundle(bundle)
    assert ok is False
    assert reason and reason.startswith("missing_field")
