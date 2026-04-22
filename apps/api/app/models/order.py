from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum

Base = declarative_base()


class OrderStatus(str, Enum):
    INTENT_SUBMITTED = "INTENT_SUBMITTED"
    INTENT_EVALUATED = "INTENT_EVALUATED"
    RECEIPT_SIGNED = "RECEIPT_SIGNED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    MATCHED_OFFCHAIN = "MATCHED_OFFCHAIN"
    ESCROW_LOCKED = "ESCROW_LOCKED"
    SETTLED_ONCHAIN = "SETTLED_ONCHAIN"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True, nullable=False)
    session_key = Column(String, index=True, nullable=False)
    wallet = Column(String, index=True, nullable=False)
    
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.INTENT_SUBMITTED, nullable=False)
    
    side = Column(String, nullable=False)
    asset = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    jurisdiction = Column(String, nullable=True)
    
    intent_data = Column(JSON, nullable=False)
    receipt_data = Column(JSON, nullable=True)
    receipt_hash = Column(String, nullable=True)
    
    yellow_order_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    evaluated_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    matched_at = Column(DateTime, nullable=True)
    settled_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    error_message = Column(String, nullable=True)
    
    def transition_to(self, new_status: OrderStatus) -> bool:
        valid_transitions = {
            OrderStatus.INTENT_SUBMITTED: [OrderStatus.INTENT_EVALUATED, OrderStatus.FAILED],
            OrderStatus.INTENT_EVALUATED: [OrderStatus.RECEIPT_SIGNED, OrderStatus.FAILED],
            OrderStatus.RECEIPT_SIGNED: [OrderStatus.ORDER_SUBMITTED, OrderStatus.FAILED],
            OrderStatus.ORDER_SUBMITTED: [OrderStatus.MATCHED_OFFCHAIN, OrderStatus.FAILED],
            OrderStatus.MATCHED_OFFCHAIN: [OrderStatus.ESCROW_LOCKED, OrderStatus.FAILED],
            OrderStatus.ESCROW_LOCKED: [OrderStatus.SETTLED_ONCHAIN, OrderStatus.FAILED],
            OrderStatus.SETTLED_ONCHAIN: [],
            OrderStatus.FAILED: [],
            OrderStatus.CANCELLED: []
        }
        
        if new_status in valid_transitions.get(self.status, []):
            self.status = new_status
            self.updated_at = datetime.utcnow()
            
            if new_status == OrderStatus.INTENT_EVALUATED:
                self.evaluated_at = datetime.utcnow()
            elif new_status == OrderStatus.ORDER_SUBMITTED:
                self.submitted_at = datetime.utcnow()
            elif new_status == OrderStatus.MATCHED_OFFCHAIN:
                self.matched_at = datetime.utcnow()
            elif new_status == OrderStatus.SETTLED_ONCHAIN:
                self.settled_at = datetime.utcnow()
            
            return True
        return False
    
    def to_dict(self):
        return {
            "order_id": self.order_id,
            "session_key": self.session_key,
            "wallet": self.wallet,
            "status": self.status.value,
            "side": self.side,
            "asset": self.asset,
            "amount": self.amount,
            "price": self.price,
            "jurisdiction": self.jurisdiction,
            "intent_data": self.intent_data,
            "receipt_hash": self.receipt_hash,
            "yellow_order_id": self.yellow_order_id,
            "created_at": self.created_at.isoformat(),
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "matched_at": self.matched_at.isoformat() if self.matched_at else None,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message
        }
