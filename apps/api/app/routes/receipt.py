import base64
import logging

from cryptography.exceptions import InvalidSignature
from fastapi import APIRouter, HTTPException

from app.models.receipt import (
    ProofBundleVerifyRequest,
    ProofBundleVerifyResponse,
)
from app.services.proof.receipt_signer import (
    ReceiptSigner,
    canonicalize,
)
from app.services.proof.store import get_bundle
from app.services.receipt_signer import public_key  # legacy module-level key

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_legacy_payload(payload: dict, signature_b64: str) -> ProofBundleVerifyResponse:
    """Backward-compatible verification of the legacy ``{payload, signature}``
    shape signed with the server's Ed25519 key over canonical JSON.
    """
    try:
        signature_bytes = base64.b64decode(signature_b64)
    except (ValueError, TypeError):
        return ProofBundleVerifyResponse(valid=False, reason="invalid_encoding")

    try:
        public_key.verify(signature_bytes, canonicalize(payload))
    except InvalidSignature:
        logger.warning("Legacy receipt verification failed: invalid signature")
        return ProofBundleVerifyResponse(valid=False, reason="invalid_signature")
    except Exception as exc:  # pragma: no cover — defensive
        logger.error("Legacy receipt verification error: %s", exc)
        return ProofBundleVerifyResponse(valid=False, reason="verification_error")

    return ProofBundleVerifyResponse(valid=True)


@router.post("/verify", response_model=ProofBundleVerifyResponse)
def verify_receipt(receipt: ProofBundleVerifyRequest) -> ProofBundleVerifyResponse:
    """Verify a proof bundle (preferred) or a legacy signed receipt.

    For proof bundles this re-canonicalises the payload, recomputes the
    ``proof_hash`` and checks the Ed25519 signature against the embedded
    ``public_key`` as well as the ``expires_at`` timestamp.
    """
    body = receipt.model_dump(exclude_none=True)

    if "proof_hash" in body:
        # New proof-bundle path.
        valid, reason = ReceiptSigner.verify_bundle(body)
        if valid:
            logger.info("Proof bundle %s verified", body.get("proof_hash"))
        else:
            logger.warning(
                "Proof bundle %s verification failed: %s",
                body.get("proof_hash"),
                reason,
            )
        return ProofBundleVerifyResponse(
            valid=valid,
            reason=reason,
            proof_hash=body.get("proof_hash"),
            expires_at=body.get("expires_at"),
        )

    # Legacy ``{payload, signature}`` path.
    if body.get("payload") is not None and body.get("signature"):
        return _verify_legacy_payload(body["payload"], body["signature"])

    return ProofBundleVerifyResponse(valid=False, reason="unrecognized_receipt_shape")


@router.get("/{proof_hash}")
def get_receipt(proof_hash: str) -> dict:
    """Return a previously-issued proof bundle by its ``proof_hash``."""
    bundle = get_bundle(proof_hash)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Proof bundle not found")
    return bundle

