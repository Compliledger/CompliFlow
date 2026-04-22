from sqlalchemy import Column, String, Integer, DateTime, JSON
from datetime import datetime
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    # ``timestamp`` is the original column kept for backward compatibility.
    # ``created_at`` is the new canonical creation timestamp; both are
    # populated to the same value for every new record.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    order_id = Column(String, index=True, nullable=True)
    session_key = Column(String, index=True, nullable=True)
    wallet = Column(String, index=True, nullable=True)
    event_type = Column(String, nullable=False, index=True)
    # ``status`` is the legacy column. ``event_status`` mirrors it under the
    # name preferred by the upgraded audit pipeline. Both are written for
    # every event so existing readers keep working.
    status = Column(String, nullable=False)
    event_status = Column(String, nullable=True, index=True)
    receipt_hash = Column(String, nullable=True)
    proof_hash = Column(String, nullable=True, index=True)
    policy_version = Column(String, nullable=True, index=True)
    reason_codes = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)
    # ``metadata`` is reserved by SQLAlchemy's DeclarativeBase, so the column
    # is stored as ``event_metadata`` but exposed as ``metadata`` in the API.
    event_metadata = Column("metadata", JSON, nullable=True)

    def to_dict(self):
        ts = self.timestamp.isoformat() if self.timestamp else None
        created = self.created_at.isoformat() if self.created_at else ts
        return {
            "id": self.id,
            "timestamp": ts,
            "created_at": created,
            "order_id": self.order_id,
            "session_key": self.session_key,
            "wallet": self.wallet,
            "event_type": self.event_type,
            "status": self.status,
            "event_status": self.event_status or self.status,
            "receipt_hash": self.receipt_hash,
            "proof_hash": self.proof_hash,
            "policy_version": self.policy_version,
            "reason_codes": self.reason_codes,
            "details": self.details,
            "metadata": self.event_metadata,
        }
