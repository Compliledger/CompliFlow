from pydantic import BaseModel


class ReceiptVerifyRequest(BaseModel):
    payload: dict
    signature: str


class ReceiptRequest(BaseModel):
    data: dict
    signature: str | None = None


class ReceiptResponse(BaseModel):
    id: int
    data: dict
    signature: str | None = None
