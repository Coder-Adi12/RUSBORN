import logging
from typing import Any

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

def list_active_knowledge() -> list[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("knowledge_base").select("*").eq("active", True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error listing active knowledge: {e!s}")
        return []

def get_knowledge_by_category(category: str) -> list[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("knowledge_base").select("*").eq("category", category).eq("active", True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching knowledge by category {category}: {e!s}")
        return []
