from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    order_id = Column(String, index=True, nullable=True)
    session_key = Column(String, index=True, nullable=True)
    wallet = Column(String, index=True, nullable=True)
    event_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    receipt_hash = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "order_id": self.order_id,
            "session_key": self.session_key,
            "wallet": self.wallet,
            "event_type": self.event_type,
            "status": self.status,
            "receipt_hash": self.receipt_hash,
            "details": self.details
        }
