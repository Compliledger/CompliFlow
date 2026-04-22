from pydantic import BaseModel


class SessionPreflightRequest(BaseModel):
    session_key: str
    wallet: str


class SessionPreflightResponse(BaseModel):
    valid: bool
    expires_at: int
    allowance_remaining: int


class OrderSubmitRequest(BaseModel):
    intent: dict
    receipt: dict


class OrderSubmitResponse(BaseModel):
    order_id: str
    status: str


class OrderStatusResponse(BaseModel):
    status: str
    details: dict
