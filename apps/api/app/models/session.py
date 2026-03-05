from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean
from datetime import datetime
from app.db.base import Base


class SessionKey(Base):
    __tablename__ = "session_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    session_key = Column(String, unique=True, index=True, nullable=False)
    wallet = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    initial_allowance = Column(Float, nullable=False)
    remaining_allowance = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        if self.remaining_allowance <= 0:
            return False
        return True
    
    def consume_allowance(self, amount: float) -> bool:
        if amount > self.remaining_allowance:
            return False
        self.remaining_allowance -= amount
        self.last_used_at = datetime.utcnow()
        return True
    
    def to_dict(self):
        return {
            "session_key": self.session_key,
            "wallet": self.wallet,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "initial_allowance": self.initial_allowance,
            "remaining_allowance": self.remaining_allowance,
            "is_active": self.is_active,
            "is_valid": self.is_valid(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None
        }
