"""Tests for date/time interpretation layer and CallContext.

These tests verify that:
1. build_system_prompt() injects the actual current date/time
2. Tool defaults use Asia/Kolkata timezone
3. The system prompt contains proper date interpretation instructions
4. CallContext prevents LLM from fabricating IDs
5. Tools return controlled errors when context is missing
"""

import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

# Set env vars before any import that triggers config
os.environ["LIVEKIT_URL"] = "dummy"
os.environ["LIVEKIT_API_KEY"] = "dummy"
os.environ["LIVEKIT_API_SECRET"] = "dummy"
os.environ["SUPABASE_URL"] = "dummy"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "dummy"

from agent_core.context import CallContext, build_call_context
from agent_core.prompts import build_system_prompt
from agent_core.tools import AppointmentTools

# --- SYSTEM PROMPT DATE INJECTION TESTS ---


class TestBuildSystemPrompt:
    def test_contains_current_date(self):
        """The prompt must contain today's actual date."""
        tz = ZoneInfo("Asia/Kolkata")
        now = datetime.now(tz)
        prompt = build_system_prompt("Asia/Kolkata")
        expected_date = now.strftime("%Y-%m-%d")
        assert expected_date in prompt

    def test_contains_current_day_of_week(self):
        tz = ZoneInfo("Asia/Kolkata")
        now = datetime.now(tz)
        prompt = build_system_prompt("Asia/Kolkata")
        expected_day = now.strftime("%A")
        assert expected_day in prompt

    def test_contains_asia_kolkata_timezone(self):
        prompt = build_system_prompt("Asia/Kolkata")
        assert "Asia/Kolkata" in prompt

    def test_does_not_contain_hardcoded_2025(self):
        prompt = build_system_prompt()
        assert "2025-05-15" not in prompt

    def test_contains_relative_date_instruction(self):
        prompt = build_system_prompt()
        assert (
            "current date provided" in prompt.lower()
            or (
                "current date" in prompt.lower()
                and "runtime" in prompt.lower()
            )
        )

    def test_contains_default_timezone_instruction(self):
        prompt = build_system_prompt()
        assert "Asia/Kolkata" in prompt

    def test_prompt_refreshes_each_call(self):
        p1 = build_system_prompt()
        p2 = build_system_prompt()
        tz = ZoneInfo("Asia/Kolkata")
        today_str = datetime.now(tz).strftime("%Y-%m-%d")
        assert today_str in p1
        assert today_str in p2

    def test_contains_id_fabrication_prohibition(self):
        """Prompt must prohibit inventing internal IDs."""
        prompt = build_system_prompt()
        assert "never invent" in prompt.lower() or (
            "never" in prompt.lower()
            and "manufacture" in prompt.lower()
        )

    def test_contains_customer_context_missing_instruction(self):
        """Prompt must instruct how to handle customer_context_missing."""
        prompt = build_system_prompt()
        assert "customer_context_missing" in prompt


# --- CALL CONTEXT TESTS ---


class TestCallContext:
    def test_empty_context(self):
        ctx = CallContext()
        assert not ctx.has_customer
        assert not ctx.has_call

    def test_context_with_customer(self):
        ctx = CallContext(customer_id="abc-123")
        assert ctx.has_customer
        assert not ctx.has_call

    def test_context_with_both(self):
        ctx = CallContext(customer_id="abc-123", call_id="call-456")
        assert ctx.has_customer
        assert ctx.has_call

    def test_build_from_metadata(self):
        import json
        meta = json.dumps({
            "customer_id": "real-uuid-here",
            "call_id": "real-call-id",
            "campaign_id": "camp-1",
            "direction": "outbound",
            "customer_name": "Test User",
        })
        ctx = build_call_context(meta)
        assert ctx.customer_id == "real-uuid-here"
        assert ctx.call_id is None
        assert ctx.direction == "outbound"
        assert ctx.customer_name == "Test User"

    def test_build_from_invalid_metadata(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_CUSTOMER_ID", None)
            ctx = build_call_context("not-valid-json")
            assert not ctx.has_customer
    def test_build_from_test_env_var(self):
        with patch.dict(os.environ, {"TEST_CUSTOMER_ID": "test-uuid-999"}):
            ctx = build_call_context(None)
            assert ctx.customer_id == "test-uuid-999"

    def test_build_with_no_context(self):
        with patch.dict(os.environ, {}, clear=False):
            # Remove TEST_CUSTOMER_ID if it exists
            os.environ.pop("TEST_CUSTOMER_ID", None)
            ctx = build_call_context(None)
            assert not ctx.has_customer


# --- TOOL DEFAULT TIMEZONE TESTS ---


class TestToolDefaults:
    """Verify the tool signatures default timezone to Asia/Kolkata."""

    @pytest.fixture
    def ctx(self):
        return CallContext(customer_id="real-cust-id", call_id="real-call-id")

    @pytest.fixture
    def tools(self, ctx):
        return AppointmentTools(ctx)

    @pytest.mark.asyncio
    async def test_check_availability_default_timezone(self, tools):
        with patch.object(tools, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"available": True}
            await tools.check_availability(date="2026-08-19", time="12:00")
            mock_post.assert_called_once_with(
                "/availability",
                {
                    "date": "2026-08-19",
                    "time": "12:00",
                    "timezone": "Asia/Kolkata",
                },
            )

    @pytest.mark.asyncio
    async def test_check_availability_explicit_timezone(self, tools):
        with patch.object(tools, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"available": True}
            await tools.check_availability(
                date="2026-08-19",
                time="12:00",
                timezone="America/New_York",
            )
            mock_post.assert_called_once_with(
                "/availability",
                {
                    "date": "2026-08-19",
                    "time": "12:00",
                    "timezone": "America/New_York",
                },
            )

    @pytest.mark.asyncio
    async def test_book_appointment_default_timezone(self, tools):
        with patch.object(tools, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}
            await tools.book_appointment(
                date="2026-08-19",
                time="12:00",
            )
            call_payload = mock_post.call_args[0][1]
            assert call_payload["timezone"] == "Asia/Kolkata"

    @pytest.mark.asyncio
    async def test_reschedule_default_timezone(self, tools):
        with patch.object(tools, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}
            await tools.reschedule_appointment(
                appointment_id="appt-1",
                new_date="2026-08-20",
                new_time="15:00",
            )
            call_payload = mock_post.call_args[0][1]
            assert call_payload["timezone"] == "Asia/Kolkata"


# --- TOOL CONTEXT INJECTION TESTS ---


class TestToolContextInjection:
    """Verify that tools inject customer_id/call_id from CallContext,
    NOT from LLM parameters."""

    @pytest.mark.asyncio
    async def test_book_injects_customer_id(self):
        """book_appointment must use customer_id from CallContext."""
        ctx = CallContext(
            customer_id="trusted-cust-uuid",
            call_id="trusted-call-uuid",
        )
        tools = AppointmentTools(ctx)
        with patch.object(tools, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}
            await tools.book_appointment(
                date="2026-08-19",
                time="12:00",
            )
            payload = mock_post.call_args[0][1]
            assert payload["customer_id"] == "trusted-cust-uuid"
            assert payload["call_id"] == "trusted-call-uuid"

    @pytest.mark.asyncio
    async def test_book_no_customer_returns_error(self):
        """book_appointment must return error when customer_id is missing."""
        ctx = CallContext()  # no customer_id
        tools = AppointmentTools(ctx)
        result = await tools.book_appointment(
            date="2026-08-19",
            time="12:00",
        )
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["error"] == "customer_context_missing"

    @pytest.mark.asyncio
    async def test_cancel_injects_customer_id(self):
        """cancel_appointment must use customer_id from CallContext."""
        ctx = CallContext(customer_id="trusted-cust-uuid")
        tools = AppointmentTools(ctx)
        with patch.object(tools, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}
            await tools.cancel_appointment(appointment_id="appt-1")
            payload = mock_post.call_args[0][1]
            assert payload["customer_id"] == "trusted-cust-uuid"
            assert payload["appointment_id"] == "appt-1"

    @pytest.mark.asyncio
    async def test_cancel_no_customer_returns_error(self):
        """cancel_appointment must return error when customer_id is missing."""
        ctx = CallContext()
        tools = AppointmentTools(ctx)
        result = await tools.cancel_appointment(appointment_id="appt-1")
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["error"] == "customer_context_missing"

    @pytest.mark.asyncio
    async def test_reschedule_injects_customer_id(self):
        """reschedule_appointment must use customer_id from CallContext."""
        ctx = CallContext(customer_id="trusted-cust-uuid")
        tools = AppointmentTools(ctx)
        with patch.object(tools, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}
            await tools.reschedule_appointment(
                appointment_id="appt-1",
                new_date="2026-08-20",
                new_time="15:00",
            )
            payload = mock_post.call_args[0][1]
            assert payload["customer_id"] == "trusted-cust-uuid"

    @pytest.mark.asyncio
    async def test_reschedule_no_customer_returns_error(self):
        ctx = CallContext()
        tools = AppointmentTools(ctx)
        result = await tools.reschedule_appointment(
            appointment_id="appt-1",
            new_date="2026-08-20",
            new_time="15:00",
        )
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["error"] == "customer_context_missing"

    @pytest.mark.asyncio
    async def test_book_no_call_id_omits_it(self):
        """If call_id is None, it should not be included in payload."""
        ctx = CallContext(customer_id="cust-1")  # no call_id
        tools = AppointmentTools(ctx)
        with patch.object(tools, "_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"success": True}
            await tools.book_appointment(
                date="2026-08-19",
                time="12:00",
            )
            payload = mock_post.call_args[0][1]
            assert "call_id" not in payload


# --- DATE RESOLUTION SCENARIOS ---


class TestDateResolutionPromptContent:
    def _get_prompt_and_now(self):
        tz = ZoneInfo("Asia/Kolkata")
        now = datetime.now(tz)
        prompt = build_system_prompt("Asia/Kolkata")
        return prompt, now

    def test_today_at_3pm_resolvable(self):
        prompt, now = self._get_prompt_and_now()
        today_str = now.strftime("%Y-%m-%d")
        assert today_str in prompt

    def test_tomorrow_at_12pm_resolvable(self):
        prompt, now = self._get_prompt_and_now()
        today_str = now.strftime("%Y-%m-%d")
        assert today_str in prompt
        assert "relative expressions" in prompt.lower()

    def test_tomorrow_at_2pm_resolvable(self):
        prompt, now = self._get_prompt_and_now()
        today_str = now.strftime("%Y-%m-%d")
        assert today_str in prompt

    def test_next_monday_resolvable(self):
        prompt, now = self._get_prompt_and_now()
        current_day = now.strftime("%A")
        assert current_day in prompt

    def test_explicit_date_format_instruction(self):
        prompt, _ = self._get_prompt_and_now()
        assert "YYYY-MM-DD" in prompt

    def test_explicit_timezone_instruction(self):
        prompt, _ = self._get_prompt_and_now()
        assert "Asia/Kolkata" in prompt

    def test_ambiguous_date_instruction(self):
        prompt, _ = self._get_prompt_and_now()
        assert "clarification" in prompt.lower() or "ask" in prompt.lower()

    def test_time_without_date_instruction(self):
        prompt, _ = self._get_prompt_and_now()
        assert (
            "most recently discussed" in prompt.lower()
            or "already been discussed" in prompt.lower()
            or "recently discussed" in prompt.lower()
        )
