"""Dashboard API router — read-only endpoints for the RUSBORN operations dashboard."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import require_dashboard_session
from services.agent_settings_service import (
    get_agent_settings,
    update_agent_settings,
)
from services.dashboard_service import (
    create_knowledge_record,
    get_analytics,
    get_appointment_detail,
    get_appointments_paginated,
    get_calendar_data,
    get_call_detail,
    get_calls_paginated,
    get_customer_profile,
    get_customers_paginated,
    get_dashboard_stats,
    get_emails_paginated,
    get_knowledge_records,
    get_system_health,
    update_knowledge_record,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_dashboard_session)],
)


# ── KPI Stats ──────────────────────────────────────────────────────────────


@router.get("/stats")
async def dashboard_stats() -> dict[str, Any]:
    """Return all KPI metrics for the dashboard."""
    stats = get_dashboard_stats()
    if not stats:
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard stats")
    return stats


# ── Calls ──────────────────────────────────────────────────────────────────


@router.get("/calls")
async def list_calls(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    return get_calls_paginated(status=status, search=search, page=page, per_page=per_page)


@router.get("/calls/{call_id}")
async def call_detail(call_id: str) -> dict[str, Any]:
    result = get_call_detail(call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Call not found")
    return result


# ── Appointments ───────────────────────────────────────────────────────────


@router.get("/appointments")
async def list_appointments(
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    return get_appointments_paginated(
        status=status, date_from=date_from, date_to=date_to,
        customer_id=customer_id, search=search, page=page, per_page=per_page,
    )


@router.get("/appointments/{appointment_id}")
async def appointment_detail(appointment_id: str) -> dict[str, Any]:
    result = get_appointment_detail(appointment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result


# ── Calendar ───────────────────────────────────────────────────────────────


@router.get("/calendar/{year}/{month}")
async def calendar_data(year: int, month: int) -> list[dict[str, Any]]:
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")
    return get_calendar_data(year, month)


# ── Customers ──────────────────────────────────────────────────────────────


@router.get("/customers")
async def list_customers(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    return get_customers_paginated(search=search, page=page, per_page=per_page)


@router.get("/customers/{customer_id}")
async def customer_profile(customer_id: str) -> dict[str, Any]:
    result = get_customer_profile(customer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


# ── Emails ─────────────────────────────────────────────────────────────────


@router.get("/emails")
async def list_emails(
    status: Optional[str] = Query(None),
    email_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    return get_emails_paginated(
        status=status, email_type=email_type, page=page, per_page=per_page,
    )


# ── Knowledge Base ─────────────────────────────────────────────────────────


@router.get("/knowledge")
async def list_knowledge(
    search: Optional[str] = Query(None),
    access_level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    return get_knowledge_records(
        search=search, access_level=access_level, page=page, per_page=per_page,
    )


class KnowledgeCreateRequest(BaseModel):
    category: str
    title: str
    content: str
    access_level: str = "PUBLIC"
    priority: int = 0
    keywords: Optional[str] = None
    source_document: Optional[str] = None


@router.post("/knowledge")
async def create_knowledge(req: KnowledgeCreateRequest) -> dict[str, Any]:
    data = req.model_dump(exclude_none=True)
    data["is_active"] = True
    result = create_knowledge_record(data)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create knowledge record")
    return result


class KnowledgeUpdateRequest(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    access_level: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    keywords: Optional[str] = None


@router.put("/knowledge/{record_id}")
async def update_knowledge(record_id: str, req: KnowledgeUpdateRequest) -> dict[str, Any]:
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = update_knowledge_record(record_id, data)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update knowledge record")
    return result


# ── Analytics ──────────────────────────────────────────────────────────────


@router.get("/analytics")
async def analytics(
    days: int = Query(30, ge=1, le=365),
) -> dict[str, Any]:
    return get_analytics(days=days)


# ── System Health ──────────────────────────────────────────────────────────


@router.get("/health")
async def system_health() -> dict[str, Any]:
    return get_system_health()


# ── Agent Settings (editable appointment configuration) ──────────────────────


class AgentSettingsUpdateRequest(BaseModel):
    appointment_timezone: Optional[str] = None
    appointment_duration_minutes: Optional[int] = None
    appointment_working_days: Optional[list[int]] = None
    appointment_start_time: Optional[str] = None
    appointment_end_time: Optional[str] = None


@router.get("/agent-settings")
async def agent_settings() -> dict[str, Any]:
    """Return the current (resolved) appointment configuration for display."""
    return get_agent_settings()


@router.put("/agent-settings")
async def update_agent_settings_endpoint(
    req: AgentSettingsUpdateRequest,
    user: str = Depends(require_dashboard_session),
) -> dict[str, Any]:
    """Validate and persist an edit to the appointment configuration.

    Both the backend (availability/booking enforcement) and the voice agent
    (spoken business hours) read from the same resolved settings, so a change
    here takes effect everywhere on the next resolution.
    """
    payload = req.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        return update_agent_settings(payload, updated_by=user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to update agent settings: {e!s}")
        raise HTTPException(
            status_code=500, detail="Failed to update agent settings"
        ) from e
