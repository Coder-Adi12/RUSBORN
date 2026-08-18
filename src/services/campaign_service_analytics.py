import logging
from typing import Any, Dict, List

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

# --- PROGRESS & ANALYTICS ---

def get_campaign_progress(campaign_id: str) -> Dict[str, Any]:
    try:
        client = get_supabase_client()
        response = client.table("campaign_contacts").select("status").eq("campaign_id", campaign_id).execute()
        contacts = response.data or []

        total = len(contacts)
        pending = sum(1 for c in contacts if c["status"] == "PENDING")
        calling = sum(1 for c in contacts if c["status"] == "CALLING")
        completed = sum(1 for c in contacts if c["status"] == "COMPLETED")
        no_answer = sum(1 for c in contacts if c["status"] == "NO_ANSWER")
        failed = sum(1 for c in contacts if c["status"] == "FAILED")
        dnc = sum(1 for c in contacts if c["status"] == "DO_NOT_CALL")
        exhausted = sum(1 for c in contacts if c["status"] == "EXHAUSTED")

        return {
            "total": total,
            "pending": pending,
            "calling": calling,
            "completed": completed,
            "no_answer": no_answer,
            "failed": failed,
            "dnc": dnc,
            "exhausted": exhausted
        }
    except Exception as e:
        logger.error(f"Error fetching campaign progress: {e!s}")
        return {}

def get_campaign_activity(campaign_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("campaign_activity").select("*").eq("campaign_id", campaign_id).order("created_at", desc=True).limit(limit).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error fetching campaign activity: {e!s}")
        return []
