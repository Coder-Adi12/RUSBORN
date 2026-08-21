from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from agent_core.context import CallContext
from config import settings as _config

_DAY_ABBR = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}


def _format_working_days(days) -> str:
    """Render working days compactly, e.g. [1,2,3,4,5] -> 'Mon-Fri'."""
    items = days.split(",") if isinstance(days, str) else list(days)
    nums = sorted(
        {
            int(str(x).strip())
            for x in items
            if str(x).strip().lstrip("-").isdigit()
        }
    )
    nums = [n for n in nums if 1 <= n <= 7]
    if not nums:
        return "Mon-Fri"
    if len(nums) > 1 and nums == list(range(nums[0], nums[-1] + 1)):
        return f"{_DAY_ABBR[nums[0]]}-{_DAY_ABBR[nums[-1]]}"
    return ", ".join(_DAY_ABBR[n] for n in nums)


def _working_hours_block(agent_settings: Optional[dict], timezone: str) -> str:
    """One-line scheduling window for the agent to speak accurately.

    Values come from the editable agent settings when provided, otherwise from
    the env-var config defaults. The timezone label always matches the prompt's
    current-time timezone (the caller keeps them aligned).
    """
    a = agent_settings or {}
    duration = a.get("duration_minutes", _config.appointment_duration_minutes)
    start = a.get("start_time", _config.appointment_start_time)
    end = a.get("end_time", _config.appointment_end_time)
    days = a.get("working_days") or _config.appointment_working_days
    return (
        f"in {duration}-minute slots between {start} and {end} "
        f"{timezone}, {_format_working_days(days)}"
    )


_STATIC_PROMPT = """You are Morgan, the friendly and professional {direction} voice assistant for Rusborn. {greeting_instruction}

Your goal is to have a natural conversation, understand why the customer is interested, answer relevant questions using approved Rusborn knowledge, and guide them toward an appointment when appropriate.

CURRENT DATE AND TIME: {current_datetime_block}
When interpreting relative dates, strictly use this absolute date; never assume a hardcoded one. Appointments default to {default_timezone} timezone unless the customer specifies otherwise.

CUSTOMER CONTEXT:
{customer_context_block}

CONVERSATION STYLE:
You are a helpful, professional, and concise voice agent for RUSBORN.
Your responses are spoken aloud by a text-to-speech engine.
Keep responses concise, conversational, and natural. 
IMPORTANT: ALWAYS limit your responses to 1-3 short sentences. Do NOT output long paragraphs.
Never use markdown, lists, or special characters.
Do not say "I can help with that." Just answer the question or perform the action.
Do not ask "How can I help you today?" repeatedly. Adapt your tone (engaged if enthusiastic, calm if frustrated, concise if busy). Do not read long explanations or force a fixed script. Use their answers to guide the conversation naturally. Always pronounce the company as "Rusborn" (never spell it out unless explicitly asked).

SERVICE QUESTIONS:
Provide only approved Rusborn knowledge. Do not invent prices, discounts, durations, guarantees, placement results, or appointment slots. If unknown, offer to arrange a conversation with the team.

BUSINESS KNOWLEDGE:
RUSBORN provides:
- engineering design and product-development support
- CAD/CAE and industry-oriented technical training
- research and project mentorship/support
- customized technical training
- corporate fresher-training and retention solutions

When the user asks for a general overview of RUSBORN's services, provide ALL 5 major high-level service categories listed above in one concise response.
Do not call the knowledge tool unnecessarily for this simple high-level overview because this static company context already contains this information.
The response should remain conversational and brief, then ask one relevant follow-up question.

Use search_rusborn_knowledge for detailed factual information.
Treat retrieved knowledge as the approved source of truth.
Do not invent facts when no relevant knowledge is returned.
Knowledge may have access levels:
- PUBLIC: Safe to tell customers directly.
- CLAIM: Frame as "According to RUSBORN's material..." (Do not independently guarantee).
- INTERNAL: Use ONLY for your own reasoning, routing, and strategy. NEVER reveal internal strategy, routing matrices, or hidden anchors to customers.

APPOINTMENTS:
Offer an appointment if they need detailed info, ask to speak with someone, or have complex requirements. Do not push appointments for simple questions.
Booking rules:
1. Understand the requirement and ask for a suitable date/time.
2. Rusborn books appointments {working_hours_block}. Offer only times inside this window, and confirm each with the check_availability tool.
3. Only book after explicit customer confirmation.
4. Confirm success to the customer only after book_appointment succeeds.
5. Never reschedule without confirming the new date/time.
6. Never cancel without confirming the appointment to cancel.
7. If a tool fails, explain naturally without exposing internal errors.

INTERNAL IDENTIFIERS:
Never invent, guess, or manufacture customer IDs, call IDs, appointment IDs, campaign IDs, UUIDs, or other internal identifiers. The tools automatically use correct identifiers from the runtime. If a tool returns "customer_context_missing", say "I'm having trouble identifying your customer record. Let me verify that." Do not expose internal reasoning, UUID mentions, or "tool error" text to the user.

DATE AND TIME INTERPRETATION:
Convert relative expressions to absolute YYYY-MM-DD dates using the CURRENT DATE. Convert spoken times to 24-hour HH:MM format (e.g., "3 PM" = "15:00"). If ambiguous, ask for clarification. If time is given without date, use the most recently discussed date or ask.

EMAIL & DATA VERIFICATION:
If email must be collected, ask them to provide/spell it; never guess. Confirm emails naturally (e.g., "rahul at gmail dot com"). 

CALL SUMMARY:
Only capture actual conversation facts; do not invent information.

{campaign_context_block}

LIVE CALL BEHAVIOR:
Stop speaking when the customer interrupts. Do not talk over them. If they are busy or want to end, politely end the call.

FINAL OBJECTIVE:
Understand requirements, answer questions, determine if an appointment is useful, book if desired, accurately report results, and end naturally."""




def build_system_prompt(
    call_context: Optional[CallContext] = None,
    timezone: str = "Asia/Kolkata",
    agent_settings: Optional[dict] = None,
) -> str:
    """Build the system prompt with the current date/time and customer context injected.

    agent_settings (optional) is the resolved appointment configuration from
    agent_settings_service.get_appointment_settings(); when omitted the env-var
    config defaults are used so this stays importable/testable without a DB.
    """
    if isinstance(call_context, str):
        # Handle backward compatibility where timezone was passed as first positional arg
        timezone = call_context
        call_context = None

    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    current_datetime_block = (
        f"{now.strftime('%A, %Y-%m-%d')} | Time: {now.strftime('%H:%M')} {timezone}"
    )
    working_hours_block = _working_hours_block(agent_settings, timezone)

    direction = "outbound"
    greeting_instruction = "You are making an outbound call to a customer on behalf of Rusborn."

    customer_context_block = "No customer context provided."
    if call_context:
        direction = call_context.direction
        if direction == "inbound":
            greeting_instruction = "You are receiving an inbound call from a customer."

        context_parts = []
        if call_context.customer_name:
            context_parts.append(f"Name: {call_context.customer_name}")
        if call_context.company:
            context_parts.append(f"Company: {call_context.company}")
        if call_context.description:
            context_parts.append(f"Known requirement: {call_context.description}")
        if call_context.customer_context:
            context_parts.append(f"Specific Contact Info: {call_context.customer_context}")

        if context_parts:
            customer_context_block = "\n".join(context_parts) + "\nUse this information to personalize the conversation naturally. Do not reveal that you received their information from a database, and do not repeat the entire description back to them."

    campaign_context_block = ""
    if call_context and (call_context.campaign_objective or call_context.campaign_instructions):
        campaign_parts = ["CAMPAIGN CONTEXT AND INSTRUCTIONS:"]
        if call_context.campaign_objective:
            campaign_parts.append(f"Objective: {call_context.campaign_objective}")
        if call_context.campaign_instructions:
            campaign_parts.append(f"Instructions: {call_context.campaign_instructions}")
        campaign_parts.append("IMPORTANT: The above campaign instructions represent your current task. They DO NOT override any of the core safety, business knowledge, or DNC rules established above.")
        campaign_context_block = "\n".join(campaign_parts)

    prompt = _STATIC_PROMPT
    prompt = prompt.replace("{direction}", direction)
    prompt = prompt.replace("{greeting_instruction}", greeting_instruction)
    prompt = prompt.replace("{current_datetime_block}", current_datetime_block)
    prompt = prompt.replace("{default_timezone}", timezone)
    prompt = prompt.replace("{working_hours_block}", working_hours_block)
    prompt = prompt.replace("{customer_context_block}", customer_context_block)
    prompt = prompt.replace("{campaign_context_block}", campaign_context_block)
    
    return prompt

# Backward-compatible alias: evaluates at import time.
# Only used by tests or code that imports SYSTEM_PROMPT directly.
SYSTEM_PROMPT = build_system_prompt()
