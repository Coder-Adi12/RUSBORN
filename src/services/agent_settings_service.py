"""Agent settings: runtime-editable appointment configuration.

A singleton row (agent_settings, id=1) holds the scheduling configuration that
was previously environment-only. Both the FastAPI backend (availability/booking
enforcement) and the LiveKit agent (spoken awareness of business hours) read
from here, so a dashboard edit takes effect everywhere.

Resolution is always defensive: any missing row / missing column / invalid value
falls back to the env-var defaults in config.settings.appointment_*, so behaviour
never regresses if the DB is unavailable or the migration has not run yet.
"""

import logging
import threading
import time as _time
from datetime import UTC, datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from config import settings
from db.client import get_supabase_client

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 30
_cache: dict[str, Any] = {"value": None, "expires_at": 0.0}
_lock = threading.Lock()

_MIN_DURATION = 5
_MAX_DURATION = 480


def _valid_tz(tz: Any) -> bool:
    if not isinstance(tz, str) or not tz.strip():
        return False
    try:
        ZoneInfo(tz)
        return True
    except Exception:
        return False


def _parse_hhmm(value: Any) -> Optional[str]:
    """Return canonical 'HH:MM' if value is a valid time string, else None."""
    if not isinstance(value, str):
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt).time().strftime("%H:%M")
        except ValueError:
            continue
    return None


def _parse_working_days(value: Any) -> Optional[list[int]]:
    """Parse working days from CSV string or list into a sorted unique int list.

    Valid ISO weekdays are 1 (Mon) .. 7 (Sun). Returns None if nothing valid.
    """
    raw: list[Any]
    if isinstance(value, str):
        raw = [p.strip() for p in value.split(",")]
    elif isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        return None

    days: set[int] = set()
    for item in raw:
        if isinstance(item, bool):
            return None
        try:
            n = int(item)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 7:
            days.add(n)
    return sorted(days) if days else None


def _config_defaults() -> dict[str, Any]:
    return {
        "appointment_timezone": settings.appointment_timezone,
        "appointment_duration_minutes": settings.appointment_duration_minutes,
        "appointment_working_days": _parse_working_days(
            settings.appointment_working_days
        )
        or [1, 2, 3, 4, 5],
        "appointment_start_time": settings.appointment_start_time,
        "appointment_end_time": settings.appointment_end_time,
        "updated_at": None,
    }


def _fetch_row() -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        resp = (
            client.table("agent_settings")
            .select("*")
            .eq("id", 1)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning(f"agent_settings fetch failed, using config defaults: {e!s}")
        return None


def _resolve_uncached() -> dict[str, Any]:
    resolved = _config_defaults()
    row = _fetch_row()
    if not row:
        return resolved

    tz = row.get("appointment_timezone")
    if _valid_tz(tz):
        resolved["appointment_timezone"] = tz

    dur = row.get("appointment_duration_minutes")
    if isinstance(dur, int) and not isinstance(dur, bool) and _MIN_DURATION <= dur <= _MAX_DURATION:
        resolved["appointment_duration_minutes"] = dur

    wd = _parse_working_days(row.get("appointment_working_days"))
    if wd:
        resolved["appointment_working_days"] = wd

    st = _parse_hhmm(row.get("appointment_start_time"))
    et = _parse_hhmm(row.get("appointment_end_time"))
    if st and et and st < et:
        resolved["appointment_start_time"] = st
        resolved["appointment_end_time"] = et

    resolved["updated_at"] = row.get("updated_at")
    return resolved


def _resolve() -> dict[str, Any]:
    # Never touch the DB during tests: keep behaviour identical to config
    # defaults and avoid coupling to per-test supabase mocks.
    if settings.environment == "test":
        return _config_defaults()

    now = _time.monotonic()
    with _lock:
        if _cache["value"] is not None and now < _cache["expires_at"]:
            return _cache["value"]

    resolved = _resolve_uncached()

    with _lock:
        _cache["value"] = resolved
        _cache["expires_at"] = _time.monotonic() + _CACHE_TTL_SECONDS
    return resolved


def invalidate_cache() -> None:
    with _lock:
        _cache["value"] = None
        _cache["expires_at"] = 0.0


def get_agent_settings() -> dict[str, Any]:
    """Public/display shape (working_days as list[int]). Used by the API."""
    return dict(_resolve())


def get_appointment_settings() -> dict[str, Any]:
    """Internal shape used by appointment_service for slot computation."""
    r = _resolve()
    return {
        "timezone": r["appointment_timezone"],
        "duration_minutes": r["appointment_duration_minutes"],
        "working_days": list(r["appointment_working_days"]),
        "start_time": r["appointment_start_time"],
        "end_time": r["appointment_end_time"],
    }


def update_agent_settings(
    payload: dict[str, Any], updated_by: Optional[str] = None
) -> dict[str, Any]:
    """Validate and persist a (possibly partial) settings update.

    Raises ValueError with a human-readable message on invalid input.
    Returns the freshly resolved settings.
    """
    current = _resolve()
    storage: dict[str, Any] = {}

    if "appointment_timezone" in payload:
        tz = payload["appointment_timezone"]
        if not _valid_tz(tz):
            raise ValueError(f"Invalid timezone: {tz!r}")
        storage["appointment_timezone"] = tz.strip()

    if "appointment_duration_minutes" in payload:
        dur = payload["appointment_duration_minutes"]
        if isinstance(dur, bool) or not isinstance(dur, int):
            raise ValueError("Duration must be an integer number of minutes")
        if not (_MIN_DURATION <= dur <= _MAX_DURATION):
            raise ValueError(
                f"Duration must be between {_MIN_DURATION} and {_MAX_DURATION} minutes"
            )
        storage["appointment_duration_minutes"] = dur

    if "appointment_working_days" in payload:
        wd = _parse_working_days(payload["appointment_working_days"])
        if not wd:
            raise ValueError(
                "Working days must contain at least one valid day (1=Mon .. 7=Sun)"
            )
        storage["appointment_working_days"] = ",".join(str(d) for d in wd)

    # Resolve the effective start/end after applying any partial override,
    # then enforce start < end across the merged values.
    new_start = current["appointment_start_time"]
    new_end = current["appointment_end_time"]
    if "appointment_start_time" in payload:
        parsed = _parse_hhmm(payload["appointment_start_time"])
        if not parsed:
            raise ValueError("Start time must be in HH:MM format")
        new_start = parsed
        storage["appointment_start_time"] = parsed
    if "appointment_end_time" in payload:
        parsed = _parse_hhmm(payload["appointment_end_time"])
        if not parsed:
            raise ValueError("End time must be in HH:MM format")
        new_end = parsed
        storage["appointment_end_time"] = parsed
    if new_start >= new_end:
        raise ValueError("Start time must be earlier than end time")

    if not storage:
        raise ValueError("No valid settings fields provided")

    storage["id"] = 1
    storage["updated_at"] = datetime.now(UTC).isoformat()
    if updated_by:
        storage["updated_by"] = updated_by

    client = get_supabase_client()
    resp = client.table("agent_settings").upsert(storage, on_conflict="id").execute()
    if not resp.data:
        raise RuntimeError("Failed to persist agent settings")

    invalidate_cache()
    return get_agent_settings()
