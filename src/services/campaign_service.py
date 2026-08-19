import logging
import os
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

def log_campaign_activity(campaign_id: str, event_type: str, message: str = "", contact_id: Optional[str] = None, attempt_id: Optional[str] = None, metadata: Optional[Dict] = None):
    try:
        client = get_supabase_client()
        data = {
            "campaign_id": campaign_id,
            "event_type": event_type,
            "message": message,
        }
        if contact_id:
            data["campaign_contact_id"] = contact_id
        if attempt_id:
            data["campaign_call_attempt_id"] = attempt_id
        if metadata:
            data["metadata"] = metadata

        client.table("campaign_activity").insert(data).execute()
    except Exception as e:
        logger.error(f"Failed to log campaign activity: {e!s}")

# --- CRUD ---

def create_campaign(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        client = get_supabase_client()
        data["status"] = "DRAFT"
        response = client.table("campaigns").insert(data).execute()
        campaign = response.data[0] if response.data else None
        if campaign:
            log_campaign_activity(campaign["id"], "CAMPAIGN_CREATED", "Campaign created in DRAFT state.")
        return campaign
    except Exception as e:
        logger.error(f"Error creating campaign: {e!s}")
        return None

def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("campaigns").select("*").eq("id", campaign_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching campaign {campaign_id}: {e!s}")
        return None

def update_campaign(campaign_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        client = get_supabase_client()
        data["updated_at"] = datetime.now(UTC).isoformat()
        response = client.table("campaigns").update(data).eq("id", campaign_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating campaign {campaign_id}: {e!s}")
        return None

def delete_campaign(campaign_id: str) -> bool:
    try:
        client = get_supabase_client()
        client.table("campaigns").delete().eq("id", campaign_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting campaign {campaign_id}: {e!s}")
        return False

def list_campaigns() -> List[Dict[str, Any]]:
    try:
        client = get_supabase_client()
        response = client.table("campaigns").select("*").order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error listing campaigns: {e!s}")
        return []

# --- CONTACTS ---

def add_contacts(campaign_id: str, customer_ids: List[str]) -> bool:
    try:
        client = get_supabase_client()
        # Filter out existing and DNC
        for cid in customer_ids:
            try:
                client.table("campaign_contacts").insert({
                    "campaign_id": campaign_id,
                    "customer_id": cid,
                    "status": "PENDING"
                }).execute()
            except Exception as e:
                logger.warning(f"Could not add contact {cid} to campaign {campaign_id}: {e!s}")
        log_campaign_activity(campaign_id, "CONTACTS_ADDED", "Added contacts to campaign.")
        return True
    except Exception as e:
        logger.error(f"Error adding contacts: {e!s}")
        return False

# --- VALIDATION ---

def validate_campaign(campaign_id: str) -> Dict[str, Any]:
    """Validates if a campaign can transition from DRAFT to READY."""
    try:
        client = get_supabase_client()
        campaign = get_campaign(campaign_id)
        if not campaign:
            return {"valid": False, "error": "Campaign not found."}

        if campaign["status"] != "DRAFT":
            return {"valid": False, "error": f"Campaign is in {campaign['status']} state, expected DRAFT."}

        errors = []
        if not campaign.get("name"): errors.append("Missing campaign name.")
        if not campaign.get("objective"): errors.append("Missing objective.")
        if not campaign.get("timezone"): errors.append("Missing timezone.")

        # Check SIP config
        if not os.getenv("LIVEKIT_SIP_TRUNK_ID"):
            errors.append("LIVEKIT_SIP_TRUNK_ID environment variable is missing. Outbound dialing cannot work.")

        # Check audience
        contacts = client.table("campaign_contacts").select("customer_id, customers(do_not_call, phone)").eq("campaign_id", campaign_id).execute().data

        if not contacts:
            errors.append("No contacts in campaign audience.")

        # Exclude DNC immediately
        valid_contacts = 0
        for c in contacts:
            if c.get("customers") and c["customers"].get("do_not_call") is True:
                client.table("campaign_contacts").update({"status": "DO_NOT_CALL"}).eq("campaign_id", campaign_id).eq("customer_id", c["customer_id"]).execute()
            elif not c.get("customers") or not c["customers"].get("phone"):
                client.table("campaign_contacts").update({"status": "FAILED", "last_error": "No phone number"}).eq("campaign_id", campaign_id).eq("customer_id", c["customer_id"]).execute()
            else:
                valid_contacts += 1

        if valid_contacts == 0 and len(contacts) > 0:
            errors.append("All contacts were excluded due to DO_NOT_CALL or missing phone numbers.")

        if errors:
            return {"valid": False, "errors": errors}

        # Transition to READY
        update_campaign(campaign_id, {"status": "READY"})
        log_campaign_activity(campaign_id, "CAMPAIGN_VALIDATED", "Campaign successfully validated and moved to READY.")
        return {"valid": True, "valid_contacts_count": valid_contacts}

    except Exception as e:
        logger.error(f"Error validating campaign {campaign_id}: {e!s}")
        return {"valid": False, "error": str(e)}

# --- STATE TRANSITIONS ---

def start_campaign(campaign_id: str) -> bool:
    try:
        campaign = get_campaign(campaign_id)
        if not campaign or campaign["status"] not in ["READY", "PAUSED", "STOPPED"]:
            return False

        update_campaign(campaign_id, {
            "status": "RUNNING",
            "started_at": datetime.now(UTC).isoformat() if not campaign.get("started_at") else campaign["started_at"]
        })
        log_campaign_activity(campaign_id, "CAMPAIGN_STARTED", "Campaign is now RUNNING.")
        return True
    except Exception as e:
        logger.error(f"Failed to start campaign {campaign_id}: {e!s}")
        return False

def pause_campaign(campaign_id: str) -> bool:
    try:
        update_campaign(campaign_id, {"status": "PAUSED", "paused_at": datetime.now(UTC).isoformat()})
        log_campaign_activity(campaign_id, "CAMPAIGN_PAUSED", "Campaign PAUSED.")
        return True
    except Exception:
        return False

def stop_campaign(campaign_id: str) -> bool:
    try:
        update_campaign(campaign_id, {"status": "STOPPED", "stopped_at": datetime.now(UTC).isoformat()})
        log_campaign_activity(campaign_id, "CAMPAIGN_STOPPED", "Campaign STOPPED.")
        return True
    except Exception:
        return False

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
