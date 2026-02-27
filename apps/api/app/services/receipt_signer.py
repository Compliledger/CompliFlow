import json
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# For MVP — generate in memory
private_key = Ed25519PrivateKey.generate()

class ReceiptSigner:

    @staticmethod
    def sign(payload: dict) -> dict:
        message = json.dumps(payload, sort_keys=True).encode()
        signature = private_key.sign(message)

        return {
            "payload": payload,
            "signature": base64.b64encode(signature).decode()
        }
