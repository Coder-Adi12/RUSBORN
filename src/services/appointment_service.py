import logging
from typing import Any, Optional

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

def get_appointment(appointment_id: str) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("appointments").select("*").eq("id", appointment_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching appointment {appointment_id}: {e!s}")
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
