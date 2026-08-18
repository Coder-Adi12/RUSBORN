import asyncio
import logging
from datetime import datetime, timezone

from db.client import get_supabase_client
from services.campaign_service import log_campaign_activity

logger = logging.getLogger(__name__)

async def claim_contact(campaign_id: str) -> dict | None:
    """Atomically claims a PENDING or retryable contact."""
    client = get_supabase_client()
    now = datetime.utcnow()

    # We want to find a contact that is either PENDING or (FAILED/NO_ANSWER and next_attempt_at <= now)
    # Since Supabase Python client complex OR queries are tricky, we'll fetch a batch of candidates 
    # and try to atomically claim the first successful one.

    response = client.table("campaign_contacts")\
        .select("*")\
        .eq("campaign_id", campaign_id)\
        .in_("status", ["PENDING", "NO_ANSWER", "FAILED"])\
        .order("priority", desc=True)\
        .order("next_attempt_at", desc=False)\
        .limit(10)\
        .execute()

    candidates = response.data or []

    for contact in candidates:
        # Check if it's eligible based on next_attempt_at
        if contact["status"] != "PENDING":
            next_attempt = contact.get("next_attempt_at")
            if next_attempt:
                next_attempt_dt = datetime.fromisoformat(next_attempt.replace("Z", "+00:00"))
                # If timezone naive, assume utc. Replace with tz aware
                if next_attempt_dt.tzinfo is None:
                    next_attempt_dt = next_attempt_dt.replace(tzinfo=timezone.utc)
                if next_attempt_dt > datetime.now(timezone.utc):
                    continue # Not ready yet

        # Try atomic claim
        claim_response = client.table("campaign_contacts")\
            .update({"status": "CALLING", "last_attempt_at": now.isoformat()})\
            .eq("id", contact["id"])\
            .eq("status", contact["status"])\
            .execute()

        if claim_response.data and len(claim_response.data) > 0:
            return claim_response.data[0]

    return None

async def orchestrate_campaign(campaign: dict):
    client = get_supabase_client()
    campaign_id = campaign["id"]
    max_concurrent = campaign.get("max_concurrent_calls", 1)

    # Check current active calls
    active_response = client.table("campaign_contacts")\
        .select("id, last_attempt_at")\
        .eq("campaign_id", campaign_id)\
        .eq("status", "CALLING")\
        .execute()

    active_contacts = active_response.data or []
    current_concurrent = len(active_contacts)

    # Reap stale CALLING contacts (e.g. if service crashed)
    # Assume a call longer than 30 mins is stale
    now = datetime.utcnow()
    for active in active_contacts:
        if active.get("last_attempt_at"):
            last_attempt = datetime.fromisoformat(active["last_attempt_at"].replace("Z", "+00:00"))
            if last_attempt.tzinfo is None:
                last_attempt = last_attempt.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - last_attempt).total_seconds() > 1800:
                logger.warning(f"Reaping stale contact {active['id']}")
                client.table("campaign_contacts").update({"status": "FAILED", "last_error": "Stale CALLING state timeout"}).eq("id", active["id"]).execute()
                current_concurrent -= 1

    available_slots = max_concurrent - current_concurrent

    if available_slots > 0:
        for _ in range(available_slots):
            claimed = await claim_contact(campaign_id)
            if claimed:
                # We successfully claimed a contact! Dispatch it.
                logger.info(f"Claimed contact {claimed['id']} for campaign {campaign_id}")

                # We need to fetch customer info
                cust_response = client.table("customers").select("*").eq("id", claimed["customer_id"]).execute()
                customer = cust_response.data[0] if cust_response.data else None

                if not customer or customer.get("do_not_call"):
                    # DNC Check directly before dial
                    client.table("campaign_contacts").update({"status": "DO_NOT_CALL"}).eq("id", claimed["id"]).execute()
                    log_campaign_activity(campaign_id, "CONTACT_SKIPPED_DNC", "Contact marked DNC right before dial.", claimed["id"])
                    continue

                # Create call attempt
                attempt_num = claimed.get("attempt_count", 0) + 1
                attempt_res = client.table("campaign_call_attempts").insert({
                    "campaign_id": campaign_id,
                    "campaign_contact_id": claimed["id"],
                    "attempt_number": attempt_num,
                    "status": "INITIATING",
                    "started_at": now.isoformat()
                }).execute()

                attempt = attempt_res.data[0] if attempt_res.data else None
                if not attempt:
                    logger.error("Failed to create attempt record")
                    continue

                # Actually Dispatch
                from services.dispatch_service import dispatch_campaign_call
                success = await dispatch_campaign_call(campaign, claimed, customer, attempt)

                if success:
                    client.table("campaign_contacts").update({"attempt_count": attempt_num}).eq("id", claimed["id"]).execute()
                    log_campaign_activity(campaign_id, "CALL_DISPATCHED", f"Dispatched attempt {attempt_num}", claimed["id"], attempt["id"])
                else:
                    # Dispatch failed synchronously
                    client.table("campaign_contacts").update({"status": "FAILED", "last_error": "Failed to dispatch SIP call"}).eq("id", claimed["id"]).execute()
                    client.table("campaign_call_attempts").update({"status": "FAILED", "error_message": "Dispatch failed", "ended_at": now.isoformat()}).eq("id", attempt["id"]).execute()

    else:
        # Check if campaign is totally done
        response = client.table("campaign_contacts")\
            .select("id")\
            .eq("campaign_id", campaign_id)\
            .in_("status", ["PENDING", "CALLING", "NO_ANSWER", "FAILED"])\
            .execute()

        remaining = response.data or []

        # Filter out those that have exhausted retries
        eligible_remaining = 0
        if remaining:
            max_attempts = campaign.get("max_attempts_per_customer", 1)
            full_remaining = client.table("campaign_contacts").select("status, attempt_count").in_("id", [r["id"] for r in remaining]).execute().data or []
            for r in full_remaining:
                if r["status"] == "CALLING" or r["status"] == "PENDING" or r["attempt_count"] < max_attempts:
                    eligible_remaining += 1
                else:
                    # Mark exhausted
                    client.table("campaign_contacts").update({"status": "EXHAUSTED"}).eq("id", r["id"]).execute()

        if eligible_remaining == 0 and current_concurrent == 0:
            logger.info(f"Campaign {campaign_id} has exhausted all contacts. Completing.")
            client.table("campaigns").update({"status": "COMPLETED", "completed_at": datetime.utcnow().isoformat()}).eq("id", campaign_id).execute()
            log_campaign_activity(campaign_id, "CAMPAIGN_COMPLETED", "No remaining eligible contacts.")

async def campaign_orchestrator_loop():
    logger.info("Starting background campaign orchestrator loop")
    while True:
        try:
            client = get_supabase_client()
            response = client.table("campaigns").select("*").eq("status", "RUNNING").execute()
            active_campaigns = response.data or []

            for campaign in active_campaigns:
                await orchestrate_campaign(campaign)

        except Exception as e:
            logger.error(f"Error in campaign orchestrator loop: {e!s}")

        await asyncio.sleep(10)
