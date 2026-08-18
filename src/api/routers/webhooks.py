import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db.client import get_supabase_client
from services.appointment_service import get_latest_appointment_by_call_id
from services.call_service import get_call_by_room_id, update_call
from services.customer_service import get_customer_by_id
from services.email_service import send_sales_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks/livekit", tags=["webhooks"])

def process_sales_summary_email(call: dict[str, Any], summary: Optional[str]) -> None:
    try:
        customer = get_customer_by_id(call["customer_id"])
        if not customer:
            logger.error(f"Customer {call['customer_id']} not found for call {call['id']}")
            return

        appointment = get_latest_appointment_by_call_id(call["id"])
        send_sales_summary(call, customer, appointment, summary)
    except Exception as e:
        logger.error(f"Failed to process sales summary email: {e}")

router = APIRouter(prefix="/api/v1/webhooks/livekit", tags=["webhooks"])

class CallSummaryWebhookRequest(BaseModel):
    job_id: str
    room_id: str
    room: str
    started_at: Optional[str] = None
    ended_at: str
    summary: Optional[str] = None

@router.post("/call-summary")
async def call_summary(req: CallSummaryWebhookRequest, background_tasks: BackgroundTasks) -> Any:
    logger.info(f"Received call summary webhook for room_id={req.room_id}")

    # 1. Fetch the existing call record
    # Note: We rely on room_id for linkage, so we don't need a customer_id from the payload.
    call = get_call_by_room_id(req.room_id)

    if not call:
        logger.warning(f"Call record not found for room_id={req.room_id}")
        return JSONResponse(status_code=404, content={"success": False, "error": "call_not_found"})

    # 2. Extract specific outcomes from structured summary if possible
    # We store the exact summary in the database without inventing facts.
    outcome = "completed"
    if req.summary:
        lower_summary = req.summary.lower()
        if "appointment booked" in lower_summary:
            outcome = "appointment_booked"
        elif "interested - follow-up required" in lower_summary:
            outcome = "interested_follow_up"
        elif "not interested" in lower_summary:
            outcome = "not_interested"
        elif "call disconnected" in lower_summary:
            outcome = "disconnected"

    # 3. Calculate duration if started_at is present
    duration_seconds = None
    if req.started_at:
        try:
            started = datetime.fromisoformat(req.started_at.replace("Z", "+00:00"))
            ended = datetime.fromisoformat(req.ended_at.replace("Z", "+00:00"))
            duration_seconds = int((ended - started).total_seconds())
        except ValueError as e:
            logger.warning(f"Failed to parse datetime for duration calculation: {e}")

    # 4. Perform idempotent update
    # If the webhook is delivered multiple times, the update is a safe overwrite of the exact same fields.
    update_data = {
        "status": "completed",
        "ended_at": req.ended_at,
        "summary": req.summary,
        "outcome": outcome,
    }

    if duration_seconds is not None:
        update_data["duration_seconds"] = duration_seconds

    try:
        updated_call = update_call(call["id"], update_data)
        if not updated_call:
            return JSONResponse(status_code=500, content={"success": False, "error": "database_error"})

        # Enqueue email tasks
        background_tasks.add_task(process_sales_summary_email, updated_call, req.summary)

        # Handle campaign logic if applicable
        if updated_call.get("campaign_id"):
            from services.dispatch_service import handle_call_outcome

            client = get_supabase_client()
            campaign_id = updated_call["campaign_id"]
            customer_id = updated_call.get("customer_id")

            # Find the contact in CALLING state for this campaign and customer
            contact_res = client.table("campaign_contacts").select("id").eq("campaign_id", campaign_id).eq("customer_id", customer_id).eq("status", "CALLING").execute()
            if contact_res.data:
                contact_id = contact_res.data[0]["id"]

                # Find the most recent attempt for this contact
                attempt_res = client.table("campaign_call_attempts").select("id").eq("campaign_contact_id", contact_id).order("attempt_number", desc=True).limit(1).execute()
                if attempt_res.data:
                    attempt_id = attempt_res.data[0]["id"]

                    # Determine final outcome based on summary/webhook
                    final_outcome = "COMPLETED"
                    if outcome == "disconnected":
                        # If disconnected very quickly, it might be NO_ANSWER
                        if duration_seconds is not None and duration_seconds < 10:
                            final_outcome = "NO_ANSWER"
                        else:
                            final_outcome = "FAILED"

                    handle_call_outcome(
                        attempt_id=attempt_id,
                        contact_id=contact_id,
                        campaign_id=campaign_id,
                        call_id=updated_call["id"],
                        outcome=final_outcome,
                        duration=duration_seconds or 0
                    )

    except Exception as e:
        logger.error(f"Failed to update call {call['id']} from webhook: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": "internal_error"})

    return {"success": True}
