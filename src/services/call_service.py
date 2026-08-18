import logging
from typing import Any, Optional

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

def create_call(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("calls").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating call: {e!s}")
        return None

def update_call(call_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("calls").update(data).eq("id", call_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating call {call_id}: {e!s}")
        return None

def get_call(call_id: str) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("calls").select("*").eq("id", call_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching call {call_id}: {e!s}")
        return None

def get_call_by_room_id(room_id: str) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("calls").select("*").eq("livekit_room_id", room_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching call by room {room_id}: {e!s}")
        return None

def create_or_reuse_call(
    customer_id: Optional[str],
    direction: str,
    livekit_room_id: str,
    started_at: str,
    campaign_id: Optional[str] = None
) -> Optional[dict[str, Any]]:
    # First, check if call already exists to ensure idempotency
    existing_call = get_call_by_room_id(livekit_room_id)
    if existing_call:
        return existing_call

    # If not, create a new one
    data = {
        "direction": direction,
        "livekit_room_id": livekit_room_id,
        "status": "in_progress",
        "started_at": started_at
    }

    if customer_id:
        data["customer_id"] = customer_id
    # Note: campaign_id is currently not in the calls table schema, but we pass it anyway 
    # just in case it gets added later. Wait, we shouldn't insert non-existent columns.
    # We will omit campaign_id from the insert for now as it's not in the models.py definition for Call.

    return create_call(data)
