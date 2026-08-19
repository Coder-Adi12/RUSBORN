import json
import logging
import os

from livekit.api import LiveKitAPI

from db.client import get_supabase_client

logger = logging.getLogger(__name__)

async def dispatch_campaign_call(campaign: dict, contact: dict, customer: dict, attempt: dict) -> bool:
    """Dispatches an outbound SIP call using LiveKit API."""
    sip_trunk_id = os.getenv("LIVEKIT_SIP_TRUNK_ID")
    agent_name = os.getenv("LIVEKIT_AGENT_NAME")

    if not sip_trunk_id or not agent_name:
        logger.error("LIVEKIT_SIP_TRUNK_ID or LIVEKIT_AGENT_NAME is not configured.")
        return False

    phone = customer.get("phone")
    if not phone:
        logger.error(f"Customer {customer.get('id')} has no phone number.")
        return False

    # DNC Check
    if customer.get("do_not_call") or contact.get("status") == "DO_NOT_CALL":
        logger.warning(f"Customer {customer.get('id')} is marked DNC. Aborting dispatch.")
        try:
            client = get_supabase_client()
            client.table("campaign_contacts").update({
                "status": "DO_NOT_CALL"
            }).eq("id", contact["id"]).execute()
        except Exception as e:
            logger.error(f"Failed to update DNC status for contact {contact['id']}: {e!s}")
        return False

    from config import settings

    url = settings.livekit_url
    api_key = settings.livekit_api_key
    api_secret = settings.livekit_api_secret

    if not all([url, api_key, api_secret]):
        logger.error("LiveKit credentials are not fully configured.")
        return False

    try:
        from livekit.api import CreateAgentDispatchRequest, CreateSIPParticipantRequest

        # Prepare job metadata which `agent.py` will parse via CallContext
        metadata_dict = {
            "direction": "outbound",
            "campaign_id": campaign["id"],
            "campaign_objective": campaign.get("objective"),
            "campaign_instructions": campaign.get("voice_agent_instructions"),
            "campaign_contact_id": contact["id"],
            "campaign_call_attempt_id": attempt["id"],
            "customer_id": customer["id"],
            "customer_name": customer.get("name"),
            "customer_phone": customer.get("phone"),
            "customer_email": customer.get("email"),
            "company": customer.get("company"),
            "description": customer.get("description"),
            "customer_context": contact.get("customer_context")
        }

        job_metadata = json.dumps(metadata_dict)
        # Append attempt number to ensure unique room and call record for retries
        room_name = f"campaign-{campaign['id'][:8]}-{contact['id'][:8]}-{attempt['attempt_number']}"

        api = LiveKitAPI(url=url, api_key=api_key, api_secret=api_secret)

        logger.info(
            "CAMPAIGN_DISPATCH_START\n"
            f"campaign_id={campaign['id']}\n"
            f"contact_id={contact['id']}\n"
            f"room={room_name}\n"
            f"agent_name={agent_name}\n"
            f"phone={phone}"
        )

        dispatch = await api.agent_dispatch.create_dispatch(
            CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=job_metadata,
            )
        )
        logger.info(f"AGENT_DISPATCH_CREATED\ndispatch_id={dispatch.id}")

        logger.info("SIP_PARTICIPANT_CREATING")
        participant = await api.sip.create_sip_participant(
            CreateSIPParticipantRequest(
                sip_trunk_id=sip_trunk_id,
                sip_call_to=phone,
                room_name=room_name,
                participant_identity="phone-user",
                participant_name=customer.get("name") or phone,
                wait_until_answered=True,
            )
        )
        logger.info(f"SIP_PARTICIPANT_CONNECTED\nparticipant_id={participant.participant_id if hasattr(participant, 'participant_id') else getattr(participant, 'id', 'unknown')}")

        await api.aclose()
        return True

    except Exception as e:
        logger.error(f"Failed to dispatch SIP call for contact {contact['id']}: {e!s}")
        return False

def handle_call_outcome(attempt_id: str, contact_id: str, campaign_id: str, call_id: str, outcome: str, duration: int):
    """
    Called when a call finishes (e.g. from webhooks or agent summary).
    outcome can be: 'COMPLETED', 'NO_ANSWER', 'FAILED'
    """
    try:
        client = get_supabase_client()
        campaign = client.table("campaigns").select("max_attempts_per_customer, retry_delay_minutes").eq("id", campaign_id).execute().data[0]
        contact = client.table("campaign_contacts").select("attempt_count").eq("id", contact_id).execute().data[0]

        from datetime import UTC
        from datetime import datetime as _dt

        # Update attempt
        client.table("campaign_call_attempts").update({
            "status": "COMPLETED" if outcome == "COMPLETED" else outcome,
            "outcome": outcome,
            "call_id": call_id,
            "ended_at": _dt.now(UTC).isoformat(),
        }).eq("id", attempt_id).execute()

        if outcome == "COMPLETED":
            client.table("campaign_contacts").update({
                "status": "COMPLETED",
                "last_outcome": outcome
            }).eq("id", contact_id).execute()
        else:
            # Need retry?
            if contact["attempt_count"] < campaign["max_attempts_per_customer"]:
                from datetime import datetime, timedelta
                next_time = datetime.now(UTC) + timedelta(minutes=campaign["retry_delay_minutes"])
                client.table("campaign_contacts").update({
                    "status": outcome, # NO_ANSWER or FAILED
                    "last_outcome": outcome,
                    "next_attempt_at": next_time.isoformat()
                }).eq("id", contact_id).execute()
            else:
                client.table("campaign_contacts").update({
                    "status": "EXHAUSTED",
                    "last_outcome": outcome
                }).eq("id", contact_id).execute()

    except Exception as e:
        logger.error(f"Error handling call outcome for attempt {attempt_id}: {e!s}")
