from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ReceiptVerifyRequest(BaseModel):
    payload: dict
    signature: str


@router.post("/verify")
def verify_receipt(receipt: ReceiptVerifyRequest):
    # Stub - always returns valid=true
    return {"valid": True}
