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
