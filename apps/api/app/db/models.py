from sqlalchemy import Column, Integer, JSON, String
from app.db.base import Base


class Intent(Base):
    __tablename__ = "intents"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(JSON, nullable=False)


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(JSON, nullable=False)
    signature = Column(String, nullable=True)
