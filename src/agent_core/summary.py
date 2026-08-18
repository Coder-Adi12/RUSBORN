import asyncio
import logging
from datetime import UTC, datetime

import aiohttp
from livekit.agents import (
    ChatContext,
    JobContext,
    ToolError,
    inference,
    utils,
)

from config import settings

logger = logging.getLogger("agent-rusborn-voice-agent")

async def summarize_session(summarizer: inference.LLM, chat_ctx: ChatContext) -> str | None:
    summary_ctx = ChatContext()
    summary_ctx.add_message(
        role="system",
        content="""Summarize the following conversation in a concise manner. Additional instructions are as follows:
Generate a concise factual summary of the call.

Use only information explicitly stated by the customer or clearly established during the conversation.

Do not invent, infer, or assume information.

Return the summary using these sections:

Customer:
Company:
Requirement:
Services interested in:
Main questions:
Pain points:
Interest level:
Appointment:
Call outcome:
Additional notes:

For fields that were not discussed, write "Not mentioned."

Interest level must be one of:
High
Medium
Low
Not determined

For appointment:
Include the confirmed appointment date, time, and timezone only if an appointment was actually booked.

Call outcome must describe the actual result, such as:
Appointment booked
Interested - follow-up required
Not interested
No appointment
Call disconnected
Could not determine

Keep the summary concise and suitable for a sales team member to read quickly.

Never claim that an email was sent, an appointment was booked, or a customer agreed to something unless that action actually succeeded or the customer explicitly confirmed it.""",
    )

    n_summarized = 0
    for item in chat_ctx.items:
        if item.type != "message":
            continue
        if item.role not in ("user", "assistant"):
            continue
        if item.extra.get("is_summary") is True:  # avoid making summary of summaries
            continue

        text = (item.text_content or "").strip()
        if text:
            summary_ctx.add_message(
                role="user",
                content=f"{item.role}: {(item.text_content or '').strip()}"
            )
            n_summarized += 1
    if n_summarized == 0:
        logger.debug("no chat messages to summarize")
        return

    response = await summarizer.chat(
        chat_ctx=summary_ctx,
        extra_kwargs={"reasoning_effort": "medium"},
    ).collect()
    return response.text.strip() if response.text else None


async def on_session_end(ctx: JobContext) -> None:
    ended_at = datetime.now(UTC)
    session = ctx._primary_agent_session
    if not session:
        logger.error("no primary agent session found for end_of_call processing")
        return

    report = ctx.make_session_report()
    summarizer = inference.LLM(model="google/gemini-3.5-flash-lite")
    summary = await summarize_session(summarizer, report.chat_history)
    # Still POST even when summary is empty — results and timing data are
    # useful to downstream consumers regardless of whether summarization
    # succeeded. Mirrors preview-agent-backend's tools.py:411-441 behavior.
    headers_dict = {}
    body = {
        "job_id": report.job_id,
        "room_id": report.room_id,
        "room": report.room,
        "started_at": datetime.fromtimestamp(report.started_at, UTC).isoformat().replace("+00:00", "Z")
            if report.started_at
            else None,
        "ended_at": ended_at.isoformat().replace("+00:00", "Z"),
        "summary": summary,
    }

    try:
        session = utils.http_context.http_session()
        timeout = aiohttp.ClientTimeout(total=10)
        resp = await asyncio.shield(session.post(
            f"{settings.backend_url}/api/v1/webhooks/livekit/call-summary", timeout=timeout, json=body, headers=headers_dict
        ))
        if resp.status >= 400:
            raise ToolError(f"error: HTTP {resp.status}: {resp.reason}")
        await resp.release()
    except ToolError:
        raise
    except (TimeoutError, aiohttp.ClientError) as e:
        raise ToolError(f"error: {e!s}") from e
