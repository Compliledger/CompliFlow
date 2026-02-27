from pydantic import BaseModel
from typing import Optional

class TradeIntent(BaseModel):
    session_key: str
    user_wallet: str
    side: str  # BUY or SELL
    amount: float
    price: float
    asset: str
    expires_at: int
    jurisdiction: Optional[str] = None
