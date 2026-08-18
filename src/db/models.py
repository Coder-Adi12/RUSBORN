from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


class Customer(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Call(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    customer_id: Optional[UUID] = None
    direction: str  # e.g., 'inbound', 'outbound'
    livekit_room_id: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    outcome: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Appointment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    customer_id: UUID
    call_id: Optional[UUID] = None
    appointment_date: str  # YYYY-MM-DD
    start_time: str        # HH:MM:SS
    end_time: str          # HH:MM:SS
    timezone: str
    status: str
    meeting_details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class KnowledgeBase(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    category: str
    title: str
    content: str
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
