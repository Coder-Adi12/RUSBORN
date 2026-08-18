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
    do_not_call: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Call(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    customer_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
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
    cancelled_at: Optional[datetime] = None
    rescheduled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    reschedule_reason: Optional[str] = None
    previous_appointment_date: Optional[str] = None
    previous_start_time: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
class KnowledgeBase(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    category: str
    title: str
    content: str
    keywords: Optional[str] = None
    access_level: str = "PUBLIC"
    source_document: Optional[str] = None
    source_page: Optional[str] = None
    is_active: bool = True
    priority: int = 100
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Campaign(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    status: str
    objective: Optional[str] = None
    voice_agent_instructions: Optional[str] = None
    timezone: str
    max_concurrent_calls: int = 1
    max_attempts_per_customer: int = 1
    retry_delay_minutes: int = 30
    scheduled_start_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CampaignContact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    customer_id: UUID
    customer_context: Optional[str] = None
    status: str = "PENDING"
    priority: int = 0
    attempt_count: int = 0
    next_attempt_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_outcome: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CampaignCallAttempt(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    campaign_contact_id: UUID
    call_id: Optional[UUID] = None
    attempt_number: int
    status: str
    outcome: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CampaignActivity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    event_type: str
    message: Optional[str] = None
    campaign_contact_id: Optional[UUID] = None
    campaign_call_attempt_id: Optional[UUID] = None
    metadata: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
