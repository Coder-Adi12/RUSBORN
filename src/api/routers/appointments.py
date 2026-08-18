import logging
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import UUID4, BaseModel, field_validator

from services.appointment_service import (
    book_appointment,
    cancel_appointment,
    check_availability,
    get_appointment,
    reschedule_appointment,
)
from services.customer_service import get_customer_by_id
from services.email_service import send_customer_confirmation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

def process_booking_email(appointment_id: str, customer_id: str) -> None:
    try:
        customer = get_customer_by_id(customer_id)
        appointment = get_appointment(appointment_id)
        if customer and appointment:
            send_customer_confirmation(appointment_id, customer, appointment)
    except Exception as e:
        logger.error(f"Failed to process booking email: {e}")

class AvailabilityRequest(BaseModel):
    date: str
    time: str
    timezone: str

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Incorrect time format, should be HH:MM")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("Invalid timezone")
        return v

class BookingRequest(BaseModel):
    customer_id: UUID4
    call_id: Optional[UUID4] = None
    date: str
    time: str
    timezone: str
    meeting_details: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Incorrect time format, should be HH:MM")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("Invalid timezone")
        return v


def handle_service_result(res: dict[str, Any]) -> Any:
    if res.get("success") or "available" in res:
        return res

    error = res.get("error", "internal_error")

    if error in ["database_error", "internal_error"]:
        return JSONResponse(status_code=500, content=res)
    elif error in ["not_found"]:
        return JSONResponse(status_code=404, content=res)
    elif error in ["slot_unavailable", "already_cancelled"] or error.startswith("cannot_reschedule") or error.startswith("cannot_cancel"):
        return JSONResponse(status_code=409, content=res)
    else:
        return JSONResponse(status_code=400, content=res)

@router.post("/availability")
async def get_availability(req: AvailabilityRequest) -> Any:
    res = check_availability(req.date, req.time, req.timezone)
    return handle_service_result(res)

@router.post("/book")
async def book(req: BookingRequest, background_tasks: BackgroundTasks) -> Any:
    res = book_appointment(
        str(req.customer_id),
        str(req.call_id) if req.call_id else None,
        req.date,
        req.time,
        req.timezone,
        req.meeting_details
    )
    if res.get("success") and "appointment_id" in res:
        background_tasks.add_task(process_booking_email, res["appointment_id"], str(req.customer_id))
    return handle_service_result(res)

class CancelRequest(BaseModel):
    appointment_id: UUID4
    customer_id: UUID4
    reason: Optional[str] = None

@router.post("/cancel")
async def cancel(req: CancelRequest) -> Any:
    res = cancel_appointment(
        str(req.appointment_id),
        str(req.customer_id),
        req.reason
    )
    return handle_service_result(res)

class RescheduleRequest(BaseModel):
    appointment_id: UUID4
    customer_id: UUID4
    date: str
    time: str
    timezone: str
    reason: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Incorrect time format, should be HH:MM")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("Invalid timezone")
        return v

@router.post("/reschedule")
async def reschedule(req: RescheduleRequest) -> Any:
    res = reschedule_appointment(
        str(req.appointment_id),
        str(req.customer_id),
        req.date,
        req.time,
        req.timezone,
        req.reason
    )
    return handle_service_result(res)
