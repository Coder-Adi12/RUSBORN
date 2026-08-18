import logging
from typing import Any

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

def search_knowledge(query: str, category: str | None = None, limit: int = 4) -> list[dict[str, Any]]:
    """Search knowledge base using full-text search via RPC.
    
    Returns concise fields: title, category, content.
    Excludes inactive entries and limits results.
    """
    try:
        client = get_supabase_client()

        # Normalize category parameter
        norm_category = category.strip() if category else None

        # Call the robust RPC search function
        response = client.rpc('search_knowledge_v1', {
            'search_query': query.strip() if query else "",
            'category_filter': norm_category,
            'max_limit': limit
        }).execute()

        safe_data = []
        if response.data:
            for row in response.data:
                if row.get("access_level") != "INTERNAL":
                    safe_data.append({
                        "title": row.get("title"),
                        "category": row.get("category"),
                        "content": row.get("content"),
                        "access_level": row.get("access_level")
                    })

        return safe_data
    except Exception as e:
        logger.error(f"Error searching knowledge for '{query}': {e!s}")
        return []

def list_active_knowledge() -> list[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("knowledge_base").select("*").eq("is_active", True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error listing active knowledge: {e!s}")
        return []

def get_knowledge_by_category(category: str) -> list[dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("knowledge_base").select("*").eq("category", category).eq("is_active", True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching knowledge by category {category}: {e!s}")
        return []
