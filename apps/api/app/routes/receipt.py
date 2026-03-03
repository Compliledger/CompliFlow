from fastapi import APIRouter
from app.models.receipt import ReceiptVerifyRequest

router = APIRouter()

@router.post("/verify")
def verify_receipt(receipt: ReceiptVerifyRequest):
    return {"valid": True}
