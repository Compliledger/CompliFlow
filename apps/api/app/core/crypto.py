import hashlib
import json
import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# For MVP — generate in memory
_private_key = Ed25519PrivateKey.generate()
_public_key = _private_key.public_key()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def sign_bytes(data: bytes) -> str:
    signature = _private_key.sign(data)
    return base64.b64encode(signature).decode()


def verify_signature(data: bytes, signature_b64: str) -> bool:
    try:
        sig = base64.b64decode(signature_b64)
        _public_key.verify(sig, data)
        return True
    except Exception:
        return False


def get_public_key_hex() -> str:
    return _public_key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
