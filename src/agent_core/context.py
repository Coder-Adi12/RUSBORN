"""CallContext: Typed runtime context for a LiveKit call.

Contains trusted identifiers (customer_id, call_id, campaign_id) that
come from the backend or job metadata — NEVER from LLM output.
"""

import logging
import os
from dataclasses import dataclass
from typing import Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class CallContext:
    """Runtime context for the current call.

    All identifiers in this object come from trusted sources:
    - Job metadata (outbound campaigns)
    - Backend phone-number lookup (inbound calls)
    - TEST_CUSTOMER_ID env var (development only)

    The LLM must never supply or modify these values.
    """

    customer_id: Optional[str] = None
    call_id: Optional[str] = None
    campaign_id: Optional[str] = None
    direction: Literal["inbound", "outbound"] = "inbound"
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None

    @property
    def has_customer(self) -> bool:
        """Return True if a real customer_id has been resolved."""
        return self.customer_id is not None

    @property
    def has_call(self) -> bool:
        """Return True if a real call_id has been resolved."""
        return self.call_id is not None


def build_call_context(job_metadata: Optional[str] = None) -> CallContext:
    """Build a CallContext from job metadata or dev env vars.

    In production:
      - Outbound: job_metadata is a JSON string with customer_id,
        campaign_id, customer info, etc.
      - Inbound: the caller phone number is used to look up the
        customer from the backend.

    In development (LiveKit Console testing):
      - TEST_CUSTOMER_ID env var provides a real customer UUID.
    """
    import json

    ctx = CallContext()

    # 1. Try to parse job metadata (production outbound flow)
    if job_metadata:
        try:
            meta = json.loads(job_metadata)
            ctx.customer_id = meta.get("customer_id")
            ctx.campaign_id = meta.get("campaign_id")
            ctx.direction = meta.get("direction", "outbound")
            ctx.customer_name = meta.get("customer_name")
            ctx.customer_email = meta.get("customer_email")
            ctx.customer_phone = meta.get("customer_phone")
            ctx.company = meta.get("company")
            ctx.description = meta.get("description")
            logger.info(
                "CallContext populated from job metadata: "
                f"customer_id={ctx.customer_id}, direction={ctx.direction}"
            )
            return ctx
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse job metadata: {e}")

    # 2. Development fallback: TEST_CUSTOMER_ID
    test_customer_id = os.getenv("TEST_CUSTOMER_ID")
    if test_customer_id:
        ctx.customer_id = test_customer_id
        ctx.direction = "inbound"
        logger.info(
            f"CallContext using TEST_CUSTOMER_ID: {test_customer_id} "
            "(development mode)"
        )
        return ctx

    # 3. No context available — the agent will operate without a
    #    customer_id. Booking will return a controlled error.
    logger.warning(
        "CallContext has no customer_id. Booking will be unavailable "
        "until the customer is identified."
    )
    return ctx
