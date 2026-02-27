from fastapi import APIRouter

router = APIRouter()

@router.post("/verify")
def verify_receipt(receipt: dict):
    # Placeholder for real verification logic
    return {"verified": True}
