import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from db.client import get_supabase_client
from services.agent_settings_service import get_appointment_settings

# Statuses that physically occupy a slot. Must stay in sync with the partial
# unique index idx_appointments_active_slot (see migration
# 20260821090000_include_rescheduled_in_active_slot.sql).
_ACTIVE_SLOT_STATUSES = ["booked", "confirmed", "rescheduled"]

logger = logging.getLogger(__name__)

def get_appointment(appointment_id: str) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("appointments").select("*").eq("id", appointment_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching appointment {appointment_id}: {e!s}")
        return None

def get_latest_appointment_by_call_id(call_id: str) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        # Fetch the most recently created booked or confirmed appointment for this call
        response = client.table("appointments") \
            .select("*") \
            .eq("call_id", call_id) \
            .in_("status", ["booked", "confirmed", "rescheduled"]) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching latest appointment for call {call_id}: {e!s}")
        return None

def list_appointments(customer_id: Optional[str] = None) -> list[dict[str, Any]]:
    try:
        client = get_supabase_client()
        query = client.table("appointments").select("*")
        if customer_id:
            query = query.eq("customer_id", customer_id)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error listing appointments: {e!s}")
        return []

def parse_time(time_str: str | time) -> time:
    """Parse time string in multiple formats or return if already a time object."""
    if isinstance(time_str, time):
        return time_str

    for fmt in ("%H:%M", "%H:%M:%S", "%H:%M:%S.%f"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            pass

    raise ValueError(f"Incorrect time format: {time_str}")

def _get_working_days() -> list[int]:
    return list(get_appointment_settings()["working_days"])

def get_slot_end_time(start_t: time, duration_mins: int) -> time:
    dummy_date = datetime.combine(datetime.today(), start_t)
    return (dummy_date + timedelta(minutes=duration_mins)).time()

def get_available_slots_for_day(target_date: date, tz_name: str) -> list[tuple[time, time]]:
    """Returns a list of all theoretically available slots for a given day in the given timezone, based on config."""
    cfg = get_appointment_settings()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(cfg["timezone"])

    working_days = list(cfg["working_days"])
    # ISO weekday(): Monday is 1, Sunday is 7.
    if target_date.isoweekday() not in working_days:
        return []

    start_time = parse_time(cfg["start_time"])
    end_time = parse_time(cfg["end_time"])
    duration = cfg["duration_minutes"]

    slots = []
    current_dt = datetime.combine(target_date, start_time).replace(tzinfo=tz)
    end_dt = datetime.combine(target_date, end_time).replace(tzinfo=tz)
    now = datetime.now(tz)

    while current_dt + timedelta(minutes=duration) <= end_dt:
        if current_dt > now:
            slot_start = current_dt.time()
            slot_end = (current_dt + timedelta(minutes=duration)).time()
            slots.append((slot_start, slot_end))
        current_dt += timedelta(minutes=duration)

    return slots

def check_availability(
    appointment_date: str,
    requested_start_time: str,
    timezone_str: str
) -> dict[str, Any]:
    try:
        req_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        req_time = parse_time(requested_start_time)
    except ValueError:
        return {"available": False, "alternatives": []}

    cfg = get_appointment_settings()
    try:
        ZoneInfo(timezone_str)
    except Exception:
        timezone_str = cfg["timezone"]

    # Get all theoretical slots
    all_slots = get_available_slots_for_day(req_date, timezone_str)
    req_end_time = get_slot_end_time(req_time, cfg["duration_minutes"])

    # Check if the requested slot is even valid theoretically
    if (req_time, req_end_time) not in all_slots:
        client = get_supabase_client()
        resp = client.table("appointments").select("start_time").eq("appointment_date", appointment_date).in_("status", _ACTIVE_SLOT_STATUSES).execute()
        booked_times = [parse_time(row["start_time"]) for row in resp.data] if resp.data else []
        alternatives = [{"start_time": s.strftime("%H:%M"), "end_time": e.strftime("%H:%M")} for s, e in all_slots if s not in booked_times]
        return {"available": False, "alternatives": alternatives[:3]}

    # Check DB for active bookings on that day
    client = get_supabase_client()
    resp = client.table("appointments").select("start_time").eq("appointment_date", appointment_date).in_("status", _ACTIVE_SLOT_STATUSES).execute()
    booked_times = [parse_time(row["start_time"]) for row in resp.data] if resp.data else []

    if req_time in booked_times:
        alternatives = [{"start_time": s.strftime("%H:%M"), "end_time": e.strftime("%H:%M")} for s, e in all_slots if s not in booked_times]
        return {"available": False, "alternatives": alternatives[:3]}

    return {
        "available": True,
        "date": appointment_date,
        "start_time": req_time.strftime("%H:%M"),
        "end_time": req_end_time.strftime("%H:%M"),
        "timezone": timezone_str
    }

def book_appointment(
    customer_id: str,
    call_id: Optional[str],
    appointment_date: str,
    start_time: str,
    timezone_str: str,
    meeting_details: Optional[str] = None
) -> dict[str, Any]:
    # Check availability again
    avail = check_availability(appointment_date, start_time, timezone_str)
    if not avail.get("available"):
        return {
            "success": False,
            "error": "slot_unavailable",
            "alternatives": avail.get("alternatives", [])
        }

    try:
        client = get_supabase_client()
        data = {
            "customer_id": customer_id,
            "call_id": call_id,
            "appointment_date": appointment_date,
            "start_time": avail["start_time"],
            "end_time": avail["end_time"],
            "timezone": timezone_str,
            "status": "booked",
            "meeting_details": meeting_details
        }
        # Assuming the database has a unique constraint on (appointment_date, start_time) where status in ('booked', 'confirmed')
        resp = client.table("appointments").insert(data).execute()

        if not resp.data:
            raise Exception("No data returned")

        inserted = resp.data[0]
        return {
            "success": True,
            "appointment_id": inserted["id"],
            "date": inserted["appointment_date"],
            "start_time": inserted["start_time"],
            "end_time": inserted["end_time"],
            "timezone": inserted["timezone"]
        }
    except Exception as e:
        err_str = str(e).lower()
        # Differentiate between unique constraint violation (slot taken) and genuine DB errors like missing columns
        if "duplicate key" in err_str or "unique constraint" in err_str or "conflict" in err_str:
            logger.warning(f"Slot conflict booking appointment: {e}")
            # Re-fetch alternatives because the slot was taken concurrently
            avail_recheck = check_availability(appointment_date, start_time, timezone_str)
            return {
                "success": False,
                "error": "slot_unavailable",
                "alternatives": avail_recheck.get("alternatives", [])
            }

        logger.error(f"Database error booking appointment: {e}")
        return {"success": False, "error": "database_error"}

def cancel_appointment(
    appointment_id: str,
    customer_id: str,
    reason: Optional[str] = None
) -> dict[str, Any]:
    client = get_supabase_client()

    # Verify appointment exists and belongs to customer
    resp = client.table("appointments").select("*").eq("id", appointment_id).eq("customer_id", customer_id).execute()
    if not resp.data:
        return {"success": False, "error": "not_found"}

    appt = resp.data[0]

    # Do not cancel an already cancelled appointment
    if appt["status"] == "cancelled":
        return {"success": False, "error": "already_cancelled"}

    # Valid transitions
    if appt["status"] in ["completed", "no_show"]:
        return {"success": False, "error": f"cannot_cancel_{appt['status']}"}

    # Update status to cancelled
    update_data = {
        "status": "cancelled",
        "cancelled_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat()
    }
    if reason:
        update_data["cancellation_reason"] = reason

    try:
        update_resp = client.table("appointments").update(update_data).eq("id", appointment_id).execute()
        if not update_resp.data:
            raise Exception("Update failed")
        return {
            "success": True,
            "appointment_id": appointment_id,
            "status": "cancelled"
        }
    except Exception as e:
        logger.error(f"Database error cancelling appointment: {e}")
        return {"success": False, "error": "database_error"}


def reschedule_appointment(
    appointment_id: str,
    customer_id: str,
    new_date: str,
    new_start_time: str,
    timezone_str: str,
    reason: Optional[str] = None
) -> dict[str, Any]:
    client = get_supabase_client()

    # 1 & 2. Verify appointment exists and belongs to customer
    resp = client.table("appointments").select("*").eq("id", appointment_id).eq("customer_id", customer_id).execute()
    if not resp.data:
        return {"success": False, "error": "not_found"}

    appt = resp.data[0]

    # 3. Verify the appointment is not cancelled or completed
    if appt["status"] in ["cancelled", "completed", "no_show"]:
        return {"success": False, "error": f"cannot_reschedule_{appt['status']}"}

    # 4, 5, 6. Check new slot availability
    avail = check_availability(new_date, new_start_time, timezone_str)
    if not avail.get("available"):
        return {
            "success": False,
            "error": "slot_unavailable",
            "alternatives": avail.get("alternatives", [])
        }

    # 9, 10, 11, 12. Update the existing appointment
    update_data = {
        "appointment_date": new_date,
        "start_time": parse_time(new_start_time).strftime("%H:%M"),
        "end_time": avail["end_time"],
        "timezone": timezone_str,
        "status": "rescheduled",
        "rescheduled_at": datetime.now(UTC).isoformat(),
        "previous_appointment_date": appt["appointment_date"],
        "previous_start_time": appt["start_time"],
        "updated_at": datetime.now(UTC).isoformat()
    }
    if reason:
        update_data["reschedule_reason"] = reason

    try:
        # 7, 8. Re-check availability inside transaction (handled by DB unique constraint on update)
        update_resp = client.table("appointments").update(update_data).eq("id", appointment_id).execute()
        if not update_resp.data:
            raise Exception("Update failed")

        inserted = update_resp.data[0]
        return {
            "success": True,
            "appointment_id": inserted["id"],
            "date": inserted["appointment_date"],
            "start_time": inserted["start_time"],
            "end_time": inserted["end_time"],
            "timezone": inserted["timezone"],
            "status": inserted["status"]
        }
    except Exception as e:
        err_str = str(e).lower()
        if "duplicate key" in err_str or "unique constraint" in err_str or "conflict" in err_str:
            logger.warning(f"Slot conflict rescheduling appointment: {e}")
            avail_recheck = check_availability(new_date, new_start_time, timezone_str)
            return {
                "success": False,
                "error": "slot_unavailable",
                "alternatives": avail_recheck.get("alternatives", [])
            }

        logger.error(f"Database error rescheduling appointment: {e}")
        return {"success": False, "error": "database_error"}
