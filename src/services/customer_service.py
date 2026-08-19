import logging
from typing import Any, Optional

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

def get_customer_by_id(customer_id: str) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("customers").select("*").eq("id", customer_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching customer by id {customer_id}: {e!s}")
        return None

def get_customer_by_phone(phone: str) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("customers").select("*").eq("phone", phone).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching customer by phone {phone}: {e!s}")
        return None

def create_customer(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("customers").insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating customer: {e!s}")
        return None

def update_customer(customer_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("customers").update(data).eq("id", customer_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating customer {customer_id}: {e!s}")
        return None

def upsert_customer_by_phone(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Upsert a customer using their phone number as the unique key.
    Requires a unique index on the phone column.
    """
    phone = data.get("phone")
    if not phone:
        logger.error("Cannot upsert customer without a phone number.")
        return None

    try:
        client = get_supabase_client()
        response = client.table("customers").upsert(
            data,
            on_conflict="phone"
        ).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error upserting customer by phone {phone}: {e!s}")
        return None
