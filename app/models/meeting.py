from app.db.base import Base
import uuid
from sqlalchemy import Column, ForeignKey, String, Text, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.orm import relationship



class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = {"schema": "assistant"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("assistant.users.id", nullable=False))  # Foreign key to User
    
    title = Column(String, index=True)
    participants = Column(JSONB, nullable=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    
    transcript = Column(JSONB, nullable=True)
    summary = Column(JSONB, nullable=True)
    merged_transcript = Column(JSONB, nullable=True)
    captions = Column(JSONB, nullable=True)
    
    user = relationship("User", back_populates="meetings")
