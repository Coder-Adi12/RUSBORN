import asyncio
import logging
from datetime import datetime, timezone

from db.client import get_supabase_client
from services.campaign_service import log_campaign_activity

logger = logging.getLogger(__name__)

async def claim_contact(campaign_id: str) -> dict | None:
    """Atomically claims a PENDING or retryable contact."""
    client = get_supabase_client()
    now = datetime.now(timezone.utc)

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

def build_dispatch_failure_update(
    attempt_number: int,
    max_attempts: int,
    retry_delay_minutes: int,
    now: datetime,
) -> dict:
    from datetime import timedelta

    update_data = {
        "attempt_count": attempt_number,
        "status": "FAILED",
        "last_error": "Failed to dispatch SIP call",
        "last_outcome": "FAILED",
    }

    if attempt_number < max_attempts:
        update_data["next_attempt_at"] = (now + timedelta(minutes=retry_delay_minutes)).isoformat()
    else:
        update_data["status"] = "EXHAUSTED"
        update_data["next_attempt_at"] = None

    return update_data


async def orchestrate_campaign(campaign: dict):
    client = get_supabase_client()
    campaign_id = campaign["id"]
    max_concurrent = campaign.get("max_concurrent_calls", 1)
    max_attempts = campaign.get("max_attempts_per_customer", 1)

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
    now = datetime.now(timezone.utc)
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
                    # Dispatch failed synchronously. Use bounded retries.
                    update_data = build_dispatch_failure_update(
                        attempt_number=attempt_num,
                        max_attempts=campaign.get("max_attempts_per_customer", 1),
                        retry_delay_minutes=campaign.get("retry_delay_minutes", 30),
                        now=now,
                    )
                    client.table("campaign_contacts").update(update_data).eq("id", claimed["id"]).execute()
                    client.table("campaign_call_attempts").update({"status": "FAILED", "error_message": "Dispatch failed", "ended_at": now.isoformat()}).eq("id", attempt["id"]).execute()

    # Evaluate completion on EVERY pass, not only when concurrency is full.
    # Previously this lived in an `else` branch of `available_slots > 0`, so a
    # campaign whose last contacts finished while a slot was free would never
    # be marked COMPLETED and stayed RUNNING forever.
    _check_and_complete_campaign(client, campaign_id, max_attempts)


def _check_and_complete_campaign(client, campaign_id: str, max_attempts: int) -> None:
    """Mark a campaign COMPLETED once no eligible contacts and no active calls remain.

    Re-reads state fresh from the DB (dispatches earlier in the same pass may
    have moved contacts to CALLING) and marks retry-exhausted contacts EXHAUSTED.
    """
    # id is required below for the EXHAUSTED update; selecting it here fixes a
    # KeyError that occurred when the projection omitted "id".
    rows = client.table("campaign_contacts")\
        .select("id, status, attempt_count")\
        .eq("campaign_id", campaign_id)\
        .in_("status", ["PENDING", "CALLING", "NO_ANSWER", "FAILED"])\
        .execute().data or []

    eligible_remaining = 0
    active_calling = 0
    for r in rows:
        status = r.get("status")
        attempts = r.get("attempt_count") or 0
        if status == "CALLING":
            active_calling += 1
            eligible_remaining += 1
        elif status == "PENDING":
            eligible_remaining += 1
        elif attempts < max_attempts:
            eligible_remaining += 1
        else:
            # Retry budget spent — retire this contact.
            client.table("campaign_contacts").update({"status": "EXHAUSTED"}).eq("id", r["id"]).execute()

    if eligible_remaining == 0 and active_calling == 0:
        logger.info(f"Campaign {campaign_id} has exhausted all contacts. Completing.")
        client.table("campaigns").update({"status": "COMPLETED", "completed_at": datetime.now(timezone.utc).isoformat()}).eq("id", campaign_id).execute()
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
