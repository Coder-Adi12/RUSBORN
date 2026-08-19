"""Appointment tools for the LiveKit agent.

These tools bridge the voice agent to the FastAPI appointment backend.
Internal identifiers (customer_id, call_id) come from CallContext,
NEVER from LLM output.
"""

import json
import logging
import time
from typing import Optional

import aiohttp
from livekit.agents import llm

from agent_core.context import CallContext
from config import settings

logger = logging.getLogger(__name__)


# Global session to optimize latency (reuse TLS connections)
_http_session: Optional[aiohttp.ClientSession] = None

def _get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(
            headers={"X-Internal-Secret": settings.internal_api_secret}
        )
    return _http_session


class AppointmentTools(llm.Toolset):
    def __init__(self, call_context: CallContext):
        super().__init__(id="appointments")
        self._ctx = call_context
        self.backend_url = settings.backend_url
        if not self.backend_url:
            self.backend_url = (
                f"http://{settings.backend_host}:{settings.backend_port}"
            )

    async def _post(self, endpoint: str, payload: dict) -> dict:
        """Helper to post to the local FastAPI backend with timeout."""
        start_time = time.monotonic()
        logger.info(f"[TOOL] {endpoint} request start")
        try:
            session = _get_http_session()
            url = f"{self.backend_url}/api/v1/appointments{endpoint}"
            async with session.post(
                url, json=payload, timeout=10.0
            ) as response:
                response_start = time.monotonic()
                logger.info(f"[TOOL] {endpoint} backend response start (latency: {response_start - start_time:.3f}s)")
                if response.status >= 500:
                    return {
                        "success": False,
                        "error": "internal_server_error",
                    }
                text = await response.text()
                response_complete = time.monotonic()
                logger.info(f"[TOOL] {endpoint} backend response complete (total duration: {response_complete - start_time:.3f}s)")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "invalid_response",
                    }
        except Exception as e:
            logger.error(f"Error calling {endpoint}: {e}")
            return {"success": False, "error": "network_error"}

    # ------------------------------------------------------------------
    # check_availability — no IDs needed
    # ------------------------------------------------------------------
    @llm.function_tool(
        description="Check if a specific time slot is available for an appointment."
    )
    async def check_availability(
        self,
        date: str,
        time: str,
        timezone: str = "Asia/Kolkata",
    ) -> str:
        """
        Check if a specific time slot is available for an appointment.

        Args:
            date: The absolute date in YYYY-MM-DD format. Resolve relative \
dates like 'tomorrow' or 'next Monday' using the current date \
from the system prompt.
            time: The start time in 24-hour HH:MM format. Convert spoken \
times like '3 PM' to '15:00'.
            timezone: The IANA timezone. Defaults to 'Asia/Kolkata'.
        """
        res = await self._post(
            "/availability",
            {"date": date, "time": time, "timezone": timezone},
        )
        return json.dumps(res)

    # ------------------------------------------------------------------
    # book_appointment — customer_id/call_id injected from CallContext
    # ------------------------------------------------------------------
    @llm.function_tool(
        description="Book a new appointment after confirming availability and customer consent."
    )
    async def book_appointment(
        self,
        date: str,
        time: str,
        timezone: str = "Asia/Kolkata",
        meeting_details: Optional[str] = "",
    ) -> str:
        """
        Book a new appointment for the customer.

        Args:
            date: The absolute date in YYYY-MM-DD format.
            time: The start time in 24-hour HH:MM format.
            timezone: The IANA timezone. Defaults to 'Asia/Kolkata'.
            meeting_details: Optional short description of the meeting purpose.
        """
        if not self._ctx.has_customer:
            return json.dumps({
                "success": False,
                "error": "customer_context_missing",
            })

        payload = {
            "customer_id": self._ctx.customer_id,
            "date": date,
            "time": time,
            "timezone": timezone,
        }
        if self._ctx.call_id:
            payload["call_id"] = self._ctx.call_id
        if meeting_details:
            payload["meeting_details"] = meeting_details

        res = await self._post("/book", payload)
        return json.dumps(res)

    # ------------------------------------------------------------------
    # cancel_appointment — customer_id injected from CallContext
    # ------------------------------------------------------------------
    @llm.function_tool(
        description="Cancel an existing appointment by ID."
    )
    async def cancel_appointment(
        self,
        appointment_id: str,
        reason: Optional[str] = "",
    ) -> str:
        """
        Cancel an existing appointment.

        Args:
            appointment_id: The appointment ID from the booking confirmation.
            reason: The reason for cancellation (optional).
        """
        if not self._ctx.has_customer:
            return json.dumps({
                "success": False,
                "error": "customer_context_missing",
            })

        payload = {
            "appointment_id": appointment_id,
            "customer_id": self._ctx.customer_id,
        }
        if reason:
            payload["reason"] = reason

        res = await self._post("/cancel", payload)
        return json.dumps(res)

    # ------------------------------------------------------------------
    # reschedule_appointment — customer_id injected from CallContext
    # ------------------------------------------------------------------
    @llm.function_tool(
        description="Reschedule an existing appointment to a new time slot."
    )
    async def reschedule_appointment(
        self,
        appointment_id: str,
        new_date: str,
        new_time: str,
        timezone: str = "Asia/Kolkata",
        reason: Optional[str] = "",
    ) -> str:
        """
        Reschedule an existing appointment to a new time slot.

        Args:
            appointment_id: The appointment ID from the booking confirmation.
            new_date: The new absolute date in YYYY-MM-DD format.
            new_time: The new start time in 24-hour HH:MM format.
            timezone: The IANA timezone. Defaults to 'Asia/Kolkata'.
            reason: The reason for rescheduling (optional).
        """
        if not self._ctx.has_customer:
            return json.dumps({
                "success": False,
                "error": "customer_context_missing",
            })

        payload = {
            "appointment_id": appointment_id,
            "customer_id": self._ctx.customer_id,
            "date": new_date,
            "time": new_time,
            "timezone": timezone,
        }
        if reason:
            payload["reason"] = reason

        res = await self._post("/reschedule", payload)
        return json.dumps(res)

    # ------------------------------------------------------------------
    # search_rusborn_knowledge — RUSBORN knowledge retrieval
    # ------------------------------------------------------------------
    @llm.function_tool(
        description="Search the RUSBORN knowledge base for factual business information, services, and capabilities."
    )
    async def search_rusborn_knowledge(
        self,
        query: str,
    ) -> str:
        """
        Search the RUSBORN knowledge base for factual business information.
        
        Args:
            query: The search text to look up in the knowledge base.
        """
        try:
            start_time = time.monotonic()
            logger.info(f"[TOOL] search_knowledge request start (query: {query})")
            # We hit the FastAPI endpoint for consistency.
            # Using the shared session for latency optimization and auth header.
            session = _get_http_session()
            url = f"{self.backend_url}/api/v1/knowledge/search"
            params = {"q": query}
            async with session.get(url, params=params, timeout=10.0) as response:
                response_start = time.monotonic()
                logger.info(f"[TOOL] search_knowledge backend response start (latency: {response_start - start_time:.3f}s)")
                if response.status >= 500:
                    return json.dumps({"success": False, "error": "internal_server_error"})
                text = await response.text()
                response_complete = time.monotonic()
                logger.info(f"[TOOL] search_knowledge backend response complete (total duration: {response_complete - start_time:.3f}s)")
                try:
                    data = json.loads(text)
                    if not data:
                        return json.dumps({"results": [], "message": "No relevant information found."})
                    return json.dumps({"results": data})
                except json.JSONDecodeError:
                    return json.dumps({"success": False, "error": "invalid_response"})
        except Exception as e:
            logger.error(f"Error calling knowledge search: {e}")
            return json.dumps({"success": False, "error": "network_error"})
