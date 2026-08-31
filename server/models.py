from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    sender = Column(String, nullable=False)
    dest = Column(String, nullable=False)
    text = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    seen = Column(Boolean, default=False)
