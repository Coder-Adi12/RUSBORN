"""Dashboard service — aggregated queries for the RUSBORN operations dashboard.

This service provides read-only aggregated data from existing tables.
It does NOT modify any existing business logic or data.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from db.client import get_supabase_client

logger = logging.getLogger(__name__)


def get_dashboard_stats() -> dict[str, Any]:
    """Return all KPI metrics for the dashboard in a single call."""
    try:
        client = get_supabase_client()
        today_str = date.today().isoformat()

        # Appointments today
        appts_today = client.table("appointments").select(
            "id, status", count="exact"
        ).eq("appointment_date", today_str).execute()

        appts_today_count = appts_today.count or 0
        appts_today_statuses = {}
        if appts_today.data:
            for a in appts_today.data:
                s = a.get("status", "unknown")
                appts_today_statuses[s] = appts_today_statuses.get(s, 0) + 1

        # Upcoming appointments (future dates, active statuses)
        upcoming = client.table("appointments").select(
            "id", count="exact"
        ).gt(
            "appointment_date", today_str
        ).in_(
            "status", ["booked", "confirmed", "rescheduled"]
        ).execute()
        upcoming_count = upcoming.count or 0

        # Active calls (in_progress)
        active_calls = client.table("calls").select(
            "id", count="exact"
        ).eq("status", "in_progress").execute()
        active_calls_count = active_calls.count or 0

        # Completed calls today
        completed_today = client.table("calls").select(
            "id", count="exact"
        ).eq("status", "completed").gte(
            "ended_at", f"{today_str}T00:00:00"
        ).execute()
        completed_today_count = completed_today.count or 0

        # Total calls today (for conversion calc)
        total_today = client.table("calls").select(
            "id", count="exact"
        ).gte("started_at", f"{today_str}T00:00:00").execute()
        total_today_count = total_today.count or 0

        # Calls with appointment_booked outcome today
        booked_today = client.table("calls").select(
            "id", count="exact"
        ).eq("outcome", "appointment_booked").gte(
            "started_at", f"{today_str}T00:00:00"
        ).execute()
        booked_today_count = booked_today.count or 0

        # Email stats
        emails_sent = client.table("email_deliveries").select(
            "id", count="exact"
        ).eq("status", "sent").execute()
        emails_pending = client.table("email_deliveries").select(
            "id", count="exact"
        ).eq("status", "pending").execute()
        emails_failed = client.table("email_deliveries").select(
            "id", count="exact"
        ).eq("status", "failed").execute()

        # Call outcomes breakdown
        outcomes = {}
        completed_calls = client.table("calls").select(
            "outcome"
        ).eq("status", "completed").execute()
        if completed_calls.data:
            for c in completed_calls.data:
                o = c.get("outcome") or "unknown"
                outcomes[o] = outcomes.get(o, 0) + 1

        return {
            "appointments_today": appts_today_count,
            "appointments_today_breakdown": appts_today_statuses,
            "upcoming_appointments": upcoming_count,
            "active_calls": active_calls_count,
            "completed_calls_today": completed_today_count,
            "total_calls_today": total_today_count,
            "bookings_today": booked_today_count,
            "booking_conversion": (
                round(booked_today_count / total_today_count * 100, 1)
                if total_today_count > 0 else 0
            ),
            "emails": {
                "sent": emails_sent.count or 0,
                "pending": emails_pending.count or 0,
                "failed": emails_failed.count or 0,
            },
            "call_outcomes": outcomes,
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        return {}


def get_calls_paginated(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Return paginated calls list with optional filters."""
    try:
        client = get_supabase_client()
        query = client.table("calls").select(
            "*, customers(id, name, company, email, phone)",
            count="exact",
        )

        if status and status != "all":
            query = query.eq("status", status)

        if search:
            query = query.or_(
                f"livekit_room_id.ilike.%{search}%,"
                f"summary.ilike.%{search}%,"
                f"outcome.ilike.%{search}%"
            )

        offset = (page - 1) * per_page
        query = query.order("created_at", desc=True).range(offset, offset + per_page - 1)
        result = query.execute()

        return {
            "data": result.data or [],
            "total": result.count or 0,
            "page": page,
            "per_page": per_page,
        }
    except Exception as e:
        logger.error(f"Error fetching calls: {e}")
        return {"data": [], "total": 0, "page": page, "per_page": per_page}


def get_call_detail(call_id: str) -> Optional[dict[str, Any]]:
    """Return a single call with customer and appointment details."""
    try:
        client = get_supabase_client()
        result = client.table("calls").select(
            "*, customers(id, name, company, email, phone)"
        ).eq("id", call_id).execute()

        if not result.data:
            return None

        call = result.data[0]

        # Fetch related appointments
        appts = client.table("appointments").select("*").eq(
            "call_id", call_id
        ).order("created_at", desc=True).execute()
        call["appointments"] = appts.data or []

        # Fetch related emails
        emails = client.table("email_deliveries").select("*").eq(
            "call_id", call_id
        ).order("created_at", desc=True).execute()
        call["emails"] = emails.data or []

        return call
    except Exception as e:
        logger.error(f"Error fetching call detail {call_id}: {e}")
        return None


def get_appointments_paginated(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Return paginated appointments with filters."""
    try:
        client = get_supabase_client()
        query = client.table("appointments").select(
            "*, customers(id, name, company, email, phone)",
            count="exact",
        )

        if status and status != "all":
            query = query.eq("status", status)
        if date_from:
            query = query.gte("appointment_date", date_from)
        if date_to:
            query = query.lte("appointment_date", date_to)
        if customer_id:
            query = query.eq("customer_id", customer_id)
        if search:
            query = query.or_(
                f"meeting_details.ilike.%{search}%,"
                f"status.ilike.%{search}%"
            )

        offset = (page - 1) * per_page
        query = query.order("appointment_date", desc=True).order(
            "start_time", desc=True
        ).range(offset, offset + per_page - 1)
        result = query.execute()

        return {
            "data": result.data or [],
            "total": result.count or 0,
            "page": page,
            "per_page": per_page,
        }
    except Exception as e:
        logger.error(f"Error fetching appointments: {e}")
        return {"data": [], "total": 0, "page": page, "per_page": per_page}


def get_appointment_detail(appointment_id: str) -> Optional[dict[str, Any]]:
    """Return a single appointment with related data."""
    try:
        client = get_supabase_client()
        result = client.table("appointments").select(
            "*, customers(id, name, company, email, phone)"
        ).eq("id", appointment_id).execute()

        if not result.data:
            return None

        appt = result.data[0]

        # Fetch related call if exists
        if appt.get("call_id"):
            call = client.table("calls").select(
                "id, status, outcome, summary, duration_seconds, started_at, ended_at"
            ).eq("id", appt["call_id"]).execute()
            appt["call"] = call.data[0] if call.data else None

        return appt
    except Exception as e:
        logger.error(f"Error fetching appointment detail {appointment_id}: {e}")
        return None


def get_calendar_data(year: int, month: int) -> list[dict[str, Any]]:
    """Return appointment counts grouped by day for a given month."""
    try:
        client = get_supabase_client()
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        result = client.table("appointments").select(
            "appointment_date, status"
        ).gte(
            "appointment_date", start_date
        ).lt(
            "appointment_date", end_date
        ).execute()

        day_data = {}
        if result.data:
            for row in result.data:
                d = row["appointment_date"]
                if d not in day_data:
                    day_data[d] = {"date": d, "total": 0, "statuses": {}}
                day_data[d]["total"] += 1
                s = row.get("status", "unknown")
                day_data[d]["statuses"][s] = day_data[d]["statuses"].get(s, 0) + 1

        return list(day_data.values())
    except Exception as e:
        logger.error(f"Error fetching calendar data: {e}")
        return []


def get_customers_paginated(
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Return paginated customers with call/appointment counts."""
    try:
        client = get_supabase_client()
        query = client.table("customers").select("*", count="exact")

        if search:
            query = query.or_(
                f"name.ilike.%{search}%,"
                f"email.ilike.%{search}%,"
                f"company.ilike.%{search}%,"
                f"phone.ilike.%{search}%"
            )

        offset = (page - 1) * per_page
        query = query.order("created_at", desc=True).range(offset, offset + per_page - 1)
        result = query.execute()

        # Enrich with counts
        customers = result.data or []
        for cust in customers:
            cid = cust["id"]
            calls_count = client.table("calls").select(
                "id", count="exact"
            ).eq("customer_id", cid).execute()
            cust["total_calls"] = calls_count.count or 0

            appts_count = client.table("appointments").select(
                "id", count="exact"
            ).eq("customer_id", cid).execute()
            cust["total_appointments"] = appts_count.count or 0

            # Last interaction
            last_call = client.table("calls").select(
                "started_at"
            ).eq("customer_id", cid).order(
                "started_at", desc=True
            ).limit(1).execute()
            cust["last_interaction"] = (
                last_call.data[0]["started_at"] if last_call.data else None
            )

        return {
            "data": customers,
            "total": result.count or 0,
            "page": page,
            "per_page": per_page,
        }
    except Exception as e:
        logger.error(f"Error fetching customers: {e}")
        return {"data": [], "total": 0, "page": page, "per_page": per_page}


def get_customer_profile(customer_id: str) -> Optional[dict[str, Any]]:
    """Return customer profile with full history."""
    try:
        client = get_supabase_client()
        result = client.table("customers").select("*").eq("id", customer_id).execute()
        if not result.data:
            return None

        customer = result.data[0]

        # Calls
        calls = client.table("calls").select(
            "id, status, outcome, summary, duration_seconds, started_at, ended_at, direction"
        ).eq("customer_id", customer_id).order("started_at", desc=True).execute()
        customer["calls"] = calls.data or []

        # Appointments
        appts = client.table("appointments").select("*").eq(
            "customer_id", customer_id
        ).order("appointment_date", desc=True).execute()
        customer["appointments"] = appts.data or []

        # Emails
        emails = client.table("email_deliveries").select("*").eq(
            "customer_id", customer_id
        ).order("created_at", desc=True).execute()
        customer["emails"] = emails.data or []

        return customer
    except Exception as e:
        logger.error(f"Error fetching customer profile {customer_id}: {e}")
        return None


def get_emails_paginated(
    status: Optional[str] = None,
    email_type: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Return paginated email deliveries."""
    try:
        client = get_supabase_client()
        query = client.table("email_deliveries").select(
            "*, customers(id, name, email)",
            count="exact",
        )

        if status and status != "all":
            query = query.eq("status", status)
        if email_type:
            query = query.eq("email_type", email_type)

        offset = (page - 1) * per_page
        query = query.order("created_at", desc=True).range(offset, offset + per_page - 1)
        result = query.execute()

        return {
            "data": result.data or [],
            "total": result.count or 0,
            "page": page,
            "per_page": per_page,
        }
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return {"data": [], "total": 0, "page": page, "per_page": per_page}


def get_knowledge_records(
    search: Optional[str] = None,
    access_level: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Return knowledge base records for dashboard management.

    Unlike the voice agent search, this returns ALL access levels
    since dashboard users are internal RUSBORN team members.
    """
    try:
        client = get_supabase_client()
        query = client.table("knowledge_base").select("*", count="exact")

        if search:
            query = query.or_(
                f"title.ilike.%{search}%,"
                f"content.ilike.%{search}%,"
                f"category.ilike.%{search}%"
            )
        if access_level:
            query = query.eq("access_level", access_level)

        offset = (page - 1) * per_page
        query = query.order("priority", desc=True).order(
            "created_at", desc=True
        ).range(offset, offset + per_page - 1)
        result = query.execute()

        return {
            "data": result.data or [],
            "total": result.count or 0,
            "page": page,
            "per_page": per_page,
        }
    except Exception as e:
        logger.error(f"Error fetching knowledge records: {e}")
        return {"data": [], "total": 0, "page": page, "per_page": per_page}


def create_knowledge_record(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Create a new knowledge base record."""
    try:
        client = get_supabase_client()
        result = client.table("knowledge_base").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error creating knowledge record: {e}")
        return None


def update_knowledge_record(
    record_id: str, data: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """Update an existing knowledge base record."""
    try:
        client = get_supabase_client()
        data["updated_at"] = datetime.now(UTC).isoformat()
        result = client.table("knowledge_base").update(data).eq(
            "id", record_id
        ).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error updating knowledge record {record_id}: {e}")
        return None


def get_analytics(
    days: int = 30,
) -> dict[str, Any]:
    """Return aggregated analytics for a date range."""
    try:
        client = get_supabase_client()
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        # Calls per day
        calls = client.table("calls").select(
            "started_at, status, outcome, duration_seconds"
        ).gte("started_at", f"{cutoff}T00:00:00").order("started_at").execute()

        calls_by_day = {}
        total_duration = 0
        call_count = 0
        for c in (calls.data or []):
            day = c["started_at"][:10] if c.get("started_at") else "unknown"
            if day not in calls_by_day:
                calls_by_day[day] = {"date": day, "total": 0, "completed": 0, "failed": 0}
            calls_by_day[day]["total"] += 1
            if c.get("status") == "completed":
                calls_by_day[day]["completed"] += 1
            elif c.get("status") == "failed":
                calls_by_day[day]["failed"] += 1
            if c.get("duration_seconds"):
                total_duration += c["duration_seconds"]
                call_count += 1

        # Appointments per day
        appts = client.table("appointments").select(
            "appointment_date, status"
        ).gte("appointment_date", cutoff).order("appointment_date").execute()

        appts_by_day = {}
        for a in (appts.data or []):
            day = a["appointment_date"]
            if day not in appts_by_day:
                appts_by_day[day] = {
                    "date": day, "total": 0, "booked": 0,
                    "cancelled": 0, "completed": 0,
                }
            appts_by_day[day]["total"] += 1
            s = a.get("status", "")
            if s in appts_by_day[day]:
                appts_by_day[day][s] += 1

        # Email stats in range
        emails = client.table("email_deliveries").select(
            "status, created_at"
        ).gte("created_at", f"{cutoff}T00:00:00").execute()

        email_stats = {"sent": 0, "pending": 0, "failed": 0}
        for e in (emails.data or []):
            s = e.get("status", "")
            if s in email_stats:
                email_stats[s] += 1

        return {
            "period_days": days,
            "calls_by_day": list(calls_by_day.values()),
            "appointments_by_day": list(appts_by_day.values()),
            "avg_call_duration": (
                round(total_duration / call_count) if call_count > 0 else 0
            ),
            "total_calls": len(calls.data or []),
            "total_appointments": len(appts.data or []),
            "email_stats": email_stats,
        }
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return {}


def get_system_health() -> dict[str, Any]:
    """Check health of all system components."""
    health = {}

    # Database
    try:
        client = get_supabase_client()
        client.table("customers").select("id").limit(1).execute()
        health["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        health["database"] = {"status": "error", "message": str(e)[:100]}

    # Knowledge search
    try:
        client = get_supabase_client()
        client.rpc("search_knowledge_v1", {
            "search_query": "test",
            "category_filter": None,
            "max_limit": 1,
        }).execute()
        health["knowledge_search"] = {"status": "healthy", "message": "RPC available"}
    except Exception as e:
        health["knowledge_search"] = {"status": "error", "message": str(e)[:100]}

    # API
    health["api"] = {"status": "healthy", "message": "Running"}

    return health
