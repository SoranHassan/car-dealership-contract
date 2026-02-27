# server/models.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String, index=True)
    buyer_id = Column(String, index=True)
    file_path = Column(String)  # مسیر روی سرور
    created_at = Column(DateTime, default=datetime.utcnow)