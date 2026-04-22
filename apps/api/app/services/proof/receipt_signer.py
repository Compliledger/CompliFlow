import hashlib
import json
import base64
import logging
import time
from typing import Any, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption
)

logger = logging.getLogger(__name__)

# Default TTL for issued proof bundles (seconds).
DEFAULT_PROOF_TTL_SECONDS = 300

# Fields excluded from proof_hash computation. The proof_hash itself is also
# excluded so that the bundle can carry the hash next to the signed core.
_EXCLUDED_FROM_PROOF_HASH = ("signature", "public_key", "proof_hash")


def canonicalize(obj: Any) -> bytes:
    """Return a deterministic JSON encoding of ``obj`` suitable for hashing.

    Keys are sorted; whitespace is stripped; non-ASCII characters are preserved
    as UTF-8.  The result is byte-for-byte stable for the same logical input,
    which is the property required for cryptographic hashing.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_object(obj: Any) -> str:
    """Canonicalize ``obj`` and return its hex SHA-256 digest."""
    return sha256_hex(canonicalize(obj))


def _load_or_generate_key() -> Ed25519PrivateKey:
    from app.core.config import settings

    private_key_b64 = settings.receipt_signing_private_key_b64

    if private_key_b64:
        try:
            private_key_bytes = base64.b64decode(private_key_b64)
            return Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        except Exception as exc:
            logger.error("Failed to load Ed25519 private key from environment: %s", exc)
            raise RuntimeError(
                "Invalid RECEIPT_SIGNING_PRIVATE_KEY_B64 — check your .env file"
            ) from exc

    generated_key = Ed25519PrivateKey.generate()
    raw_private = generated_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    raw_public = generated_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    logger.warning("=" * 72)
    logger.warning("RECEIPT_SIGNING_PRIVATE_KEY_B64 is not set.")
    logger.warning("An ephemeral key has been generated. Receipts will NOT be")
    logger.warning("verifiable after a server restart.")
    logger.warning("Add the following lines to your .env file to persist signing:")
    logger.warning("")
    logger.warning(
        "RECEIPT_SIGNING_PRIVATE_KEY_B64=%s", base64.b64encode(raw_private).decode()
    )
    logger.warning(
        "RECEIPT_SIGNING_PUBLIC_KEY_B64=%s", base64.b64encode(raw_public).decode()
    )
    logger.warning("=" * 72)

    return generated_key


private_key: Ed25519PrivateKey = _load_or_generate_key()
public_key: Ed25519PublicKey = private_key.public_key()


class ReceiptSigner:

    @staticmethod
    def sign(payload: dict) -> dict:
        """Legacy signing path used by the existing intent route.

        The new proof-bundle flow should call :meth:`create_proof_bundle`,
        but this method is kept so the current frontend (which expects a
        ``{"payload": ..., "signature": ...}`` shape) continues to work.
        """
        message = canonicalize(payload)
        signature = private_key.sign(message)

        return {
            "payload": payload,
            "signature": base64.b64encode(signature).decode(),
        }

    @staticmethod
    def get_public_key_b64() -> str:
        raw_public = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return base64.b64encode(raw_public).decode()

    # ------------------------------------------------------------------
    # Proof bundle (v1.0) APIs
    # ------------------------------------------------------------------

    @staticmethod
    def create_proof_bundle(
        decision: dict,
        wallet: str,
        session_key: str,
        intent: Optional[dict] = None,
        ttl_seconds: int = DEFAULT_PROOF_TTL_SECONDS,
        proof_version: str = "1.0",
        issued_at: Optional[int] = None,
    ) -> dict:
        """Build a signed proof bundle.

        The bundle is intentionally generic so it can attest to any kind of
        compliance decision (execution approval today, settlement validation
        tomorrow, ...).  The payload that is hashed and signed contains
        everything except ``signature`` / ``public_key`` / ``proof_hash``.
        """
        if not wallet:
            raise ValueError("wallet is required to create a proof bundle")
        if not session_key:
            raise ValueError("session_key is required to create a proof bundle")

        now = int(issued_at if issued_at is not None else time.time())
        expires_at = now + int(ttl_seconds)

        intent_hash = hash_object(intent) if intent is not None else hash_object({})
        decision_hash = hash_object(decision)
        session_key_hash = sha256_hex(session_key.encode("utf-8"))

        core = {
            "proof_version": proof_version,
            "issued_at": now,
            "expires_at": expires_at,
            "intent_hash": intent_hash,
            "decision_hash": decision_hash,
            "wallet": wallet,
            "session_key_hash": session_key_hash,
            "decision": decision,
        }

        proof_hash = sha256_hex(canonicalize(core))
        signature = private_key.sign(proof_hash.encode("utf-8"))

        bundle = dict(core)
        bundle["proof_hash"] = proof_hash
        bundle["signature"] = base64.b64encode(signature).decode()
        bundle["public_key"] = ReceiptSigner.get_public_key_b64()
        return bundle

    @staticmethod
    def _recompute_proof_hash(bundle: dict) -> str:
        core = {k: v for k, v in bundle.items() if k not in _EXCLUDED_FROM_PROOF_HASH}
        return sha256_hex(canonicalize(core))

    @staticmethod
    def verify_bundle(bundle: dict, now: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """Verify a proof bundle.

        Returns ``(True, None)`` when the bundle is well-formed, the
        ``proof_hash`` matches the canonicalised payload, the Ed25519
        signature is valid, and the bundle has not expired.  Otherwise
        returns ``(False, reason)``.
        """
        required = (
            "proof_version", "issued_at", "expires_at", "intent_hash",
            "decision_hash", "proof_hash", "wallet", "session_key_hash",
            "decision", "signature", "public_key",
        )
        for field in required:
            if field not in bundle:
                return False, f"missing_field:{field}"

        recomputed = ReceiptSigner._recompute_proof_hash(bundle)
        if recomputed != bundle["proof_hash"]:
            return False, "proof_hash_mismatch"

        try:
            pub_bytes = base64.b64decode(bundle["public_key"])
            sig_bytes = base64.b64decode(bundle["signature"])
        except (ValueError, TypeError):
            return False, "invalid_encoding"

        try:
            verifier = Ed25519PublicKey.from_public_bytes(pub_bytes)
            verifier.verify(sig_bytes, bundle["proof_hash"].encode("utf-8"))
        except InvalidSignature:
            return False, "invalid_signature"
        except Exception as exc:  # malformed key, etc.
            logger.warning("Proof bundle verification error: %s", exc)
            return False, "verification_error"

        current = int(now if now is not None else time.time())
        if current > int(bundle["expires_at"]):
            return False, "expired"

        return True, None
