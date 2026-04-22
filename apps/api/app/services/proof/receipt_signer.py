import json
import base64
import logging
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption
)

logger = logging.getLogger(__name__)


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
        message = json.dumps(payload, sort_keys=True).encode()
        signature = private_key.sign(message)

        return {
            "payload": payload,
            "signature": base64.b64encode(signature).decode(),
        }

    @staticmethod
    def get_public_key_b64() -> str:
        raw_public = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return base64.b64encode(raw_public).decode()
