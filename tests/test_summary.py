from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_core.summary import on_session_end


@pytest.fixture
def mock_job_ctx():
    ctx = MagicMock()
    ctx.room.name = "console-test123"
    ctx._primary_agent_session = MagicMock()

    report = MagicMock()
    report.job_id = "job_123"
    report.room_id = "RM_tQzK65SnipHg" # Internal LiveKit SID
    report.room = "console-test123"
    report.started_at = datetime.now(UTC).timestamp()
    report.chat_history = MagicMock()

    ctx.make_session_report.return_value = report
    return ctx

@pytest.mark.asyncio
async def test_on_session_end_success(mock_job_ctx):
    with patch("agent_core.summary.summarize_session", new_callable=AsyncMock) as mock_summarize, \
         patch("agent_core.summary.utils.http_context.http_session") as mock_http:

        mock_summarize.return_value = "Test summary"

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_resp)
        mock_http.return_value = mock_session

        await on_session_end(mock_job_ctx)

        # Verify summary was generated
        mock_summarize.assert_called_once()

        # Verify webhook was sent
        mock_session.post.assert_called_once()

        # Verify correct room_id mapping (regression test for RM_... SID)
        post_kwargs = mock_session.post.call_args[1]
        payload = post_kwargs["json"]
        assert payload["room_id"] == "console-test123"
        assert payload["room_id"] != "RM_tQzK65SnipHg"

@pytest.mark.asyncio
async def test_on_session_end_summary_failure(mock_job_ctx):
    with patch("agent_core.summary.summarize_session", new_callable=AsyncMock) as mock_summarize, \
         patch("agent_core.summary.utils.http_context.http_session") as mock_http, \
         patch("agent_core.summary.logger.error") as mock_logger:

        # Simulate summary generation failure
        mock_summarize.side_effect = Exception("Summary generation failed")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_resp)
        mock_http.return_value = mock_session

        # Should not raise exception
        await on_session_end(mock_job_ctx)

        # Webhook should still be sent
        mock_session.post.assert_called_once()

        # Verify error was logged
        mock_logger.assert_any_call("Failed to generate summary: Summary generation failed")

@pytest.mark.asyncio
async def test_on_session_end_webhook_failure_status(mock_job_ctx):
    with patch("agent_core.summary.summarize_session", new_callable=AsyncMock) as mock_summarize, \
         patch("agent_core.summary.utils.http_context.http_session") as mock_http, \
         patch("agent_core.summary.logger.error") as mock_logger:

        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.reason = "Internal Server Error"
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_resp)
        mock_http.return_value = mock_session

        # Should not raise exception
        await on_session_end(mock_job_ctx)

        # Verify webhook was sent
        mock_session.post.assert_called_once()

        # Verify error was logged

        mock_logger.assert_any_call("Webhook failed with status 500: Internal Server Error")

@pytest.mark.asyncio
async def test_on_session_end_webhook_network_failure(mock_job_ctx):
    with patch("agent_core.summary.summarize_session", new_callable=AsyncMock) as mock_summarize, \
         patch("agent_core.summary.utils.http_context.http_session") as mock_http, \
         patch("agent_core.summary.logger.error") as mock_logger:

        mock_session = MagicMock()
        mock_session.post = AsyncMock(side_effect=Exception("Connection Refused"))
        mock_http.return_value = mock_session

        # Should not raise exception
        await on_session_end(mock_job_ctx)

        # Verify error was logged
        mock_logger.assert_any_call("Webhook HTTP request failed: Connection Refused")
