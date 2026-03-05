import json
import base64
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from cryptography.exceptions import InvalidSignature
from app.services.receipt_signer import public_key

logger = logging.getLogger(__name__)

router = APIRouter()


class ReceiptVerifyRequest(BaseModel):
    payload: dict
    signature: str


@router.post("/verify")
def verify_receipt(receipt: ReceiptVerifyRequest):
    try:
        signature_bytes = base64.b64decode(receipt.signature)
        message = json.dumps(receipt.payload, sort_keys=True).encode()
        public_key.verify(signature_bytes, message)
        logger.info("Receipt verification succeeded for payload hash check")
        return {"valid": True}
    except InvalidSignature:
        logger.warning("Receipt verification failed: invalid signature")
        return {"valid": False, "reason": "invalid_signature"}
    except (ValueError, Exception) as exc:
        logger.error("Receipt verification error: %s", exc)
        return {"valid": False, "reason": f"verification_error: {exc}"}
