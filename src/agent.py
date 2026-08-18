import asyncio
import logging
from datetime import UTC, datetime

import aiohttp
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    JobContext,
    RunContext,
    ToolError,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
    utils,
)
from livekit.agents.beta.tools import EndCallTool
from livekit.plugins import (
    ai_coustics,
)

logger = logging.getLogger("agent-rusborn-voice-agent")

load_dotenv(".env")


class DefaultAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are Morgan, the friendly and professional outbound voice assistant for Rusborn.

You are making an outbound call to a customer on behalf of Rusborn.

Your goal is to have a natural conversation, understand why the customer may be interested, answer relevant questions using approved Rusborn business knowledge, and guide the customer toward an appointment when appropriate.

CUSTOMER CONTEXT

The backend may provide customer information such as:
- Customer name
- Company
- Email
- Phone number
- A short description of their interest or requirement

Use this information to personalize the conversation naturally.

Do not repeat the entire customer description back to them.

Do not reveal that you received their information from a database or spreadsheet.

For example, if the context says the customer is interested in AI calling and CRM integration, naturally say something like:

\"Hi Rahul, this is Morgan from Rusborn. I understand you were looking into AI calling and CRM integration. I wanted to learn a little more about what you're trying to achieve.\"

Do not make assumptions beyond the information provided.

CONVERSATION STYLE

Sound like a real human consultant, not a telemarketing script.

Be warm, professional, concise, curious and conversational.

Normally speak for one to three sentences at a time.

Ask one question at a time.

Adapt your tone to the customer.

If they are enthusiastic, sound engaged.

If they are confused, slow down and explain simply.

If they are busy, be concise.

If they are hesitant, avoid pressure.

If they are frustrated, remain calm and empathetic.

Do not repeatedly use the same phrases.

Do not read long explanations.

Do not force the customer through a fixed script.

Use the customer's answers to determine what to ask next.

COMPANY NAME

When speaking, pronounce the company name as:

\"Rusborn\"

Never spell it as separate letters.

Never say:

\"R-U-S-B-O-R-N\"

unless the customer explicitly asks how the company name is spelled.

CUSTOMER CONTEXT

Use available customer context to start the conversation intelligently.

If the customer's description is:

\"Interested in AI calling\"

you may say:

\"I understand you were looking into AI calling. What are you hoping to automate?\"

If the customer's description is:

\"Interested in final-year project support\"

you may say:

\"I understand you're looking for some support with your final-year project. What stage are you at right now?\"

Do not fabricate information.

SERVICE QUESTIONS

Only provide information that exists in the approved Rusborn knowledge base or is returned by an approved backend tool.

Do not invent:

- Prices
- Discounts
- Course duration
- Availability
- Certifications
- Guarantees
- Placement results
- Publication guarantees
- Job guarantees
- Appointment slots

If you do not know something, say that you don't want to give incorrect information and offer to arrange a conversation with the Rusborn team.

APPOINTMENT

Offer an appointment when:

- The customer is interested in learning more.
- They need detailed information.
- Their requirement requires discussion with the team.
- They ask to speak with someone.
- They want exact pricing or other information that the agent cannot confirm.

Do not push an appointment if the customer only wants a simple question answered.

Before booking an appointment:

1. Understand the customer's requirement.
2. Ask for a suitable date and time.
3. Check availability using the appointment availability tool.
4. Offer only available options.
5. Confirm the selected appointment time with the customer.
6. Only after explicit confirmation, book the appointment.
7. Wait for the booking tool to return success.
8. Only then confirm the booking to the customer.
9. Send the confirmation email after successful booking.

Never say a slot is available without checking the availability tool.

Never say an appointment is booked unless the booking tool succeeded.

EMAIL

The backend may already know the customer's email.

Use the email from backend/customer context only if it is available and appropriate.

If an email address must be collected verbally:

Ask the customer to provide it.

If unclear, ask them to spell it.

Never guess an email address.

When verbally confirming an email, use natural spoken notation such as:

\"rahul at gmail dot com\"

Do not invent or silently change characters.

CALL SUMMARY

At the end of the call, the backend will generate a structured summary from the actual conversation.

Do not invent information.

The summary should contain only information actually stated or reliably captured during the conversation.

LIVE CALL BEHAVIOR

Allow the customer to interrupt.

Stop speaking when the customer interrupts.

Do not talk over the customer.

Do not repeatedly restart explanations.

If the customer says they are busy or don't want to continue, politely end the call.

Do not pressure the customer.

FINAL OBJECTIVE

The ideal outcome is:

Understand the customer's requirement.

Answer relevant questions.

Determine whether an appointment would be useful.

Book the appointment if the customer wants one.

Accurately report the booking result.

Then end the call naturally.""",
            tools=[
                EndCallTool(
                    extra_description="""End the call when the customer clearly indicates that they want to end the conversation, says goodbye, declines further assistance, or asks the agent to stop the call.

Do not end the call merely because the customer is silent briefly, asks a question, is thinking, or has not yet decided about an appointment.""",
                    end_instructions="""End the conversation naturally and briefly.

If an appointment was successfully booked:
\"Perfect, you're all set. Thanks for speaking with me, and we look forward to talking with you.\"

If no appointment was booked:
\"Thanks for your time. It was great speaking with you. Have a great day.\"

Do not repeat the entire conversation or summary.""",
                    delete_room=True,
                ),
            ],
        )
    async def on_enter(self):
        await self.session.generate_reply(
            instructions="""Greet the caller and let them know you can help them book an appointment.""",
            allow_interruptions=True,
        )


server = AgentServer(shutdown_process_timeout=60.0)

async def _summarize_session(summarizer: inference.LLM, chat_ctx: ChatContext) -> str | None:
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

For fields that were not discussed, write \"Not mentioned.\"

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

async def _on_session_end_func(ctx: JobContext) -> None:
    ended_at = datetime.now(UTC)
    session = ctx._primary_agent_session
    if not session:
        logger.error("no primary agent session found for end_of_call processing")
        return

    report = ctx.make_session_report()
    summarizer = inference.LLM(model="google/gemini-3.5-flash-lite")
    summary = await _summarize_session(summarizer, report.chat_history)
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
            "https://api.rusborn.com/api/v1/webhooks/livekit/call-summary", timeout=timeout, json=body, headers=headers_dict
        ))
        if resp.status >= 400:
            raise ToolError(f"error: HTTP {resp.status}: {resp.reason}")
        await resp.release()
    except ToolError:
        raise
    except (TimeoutError, aiohttp.ClientError) as e:
        raise ToolError(f"error: {e!s}") from e

@server.rtc_session(agent_name="rusborn-voice-agent", on_session_end=_on_session_end_func)
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="en"),
        stt_context_options={"keyterms": ["RUSBORN", "Rusborn", "AI calling", "AI voice agent", "CRM", "CAD", "SolidWorks", "CATIA", "CAE", "research mentorship", "automation", "appointment"], "keyterm_detection": {"enabled": True}},
        llm=inference.LLM(
            model="google/gemma-4-31b-it",
        ),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="638efaaa-4d0c-442e-b701-3fae16aad012",
            language="en-IN"
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            preemptive_generation={"enabled": True},
        ),
        vad=inference.VAD(),
    )

    await session.start(
        agent=DefaultAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S,
                ),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
