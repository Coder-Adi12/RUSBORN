import logging
from datetime import datetime

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
)
from livekit.agents.beta.tools import EndCallTool
from livekit.plugins import ai_coustics

from agent_core.context import CallContext, build_call_context
from agent_core.prompts import build_system_prompt
from agent_core.summary import on_session_end
from agent_core.tools import AppointmentTools
from services.call_service import create_or_reuse_call

logger = logging.getLogger("agent-rusborn-voice-agent")


class DefaultAgent(Agent):
    def __init__(self, call_context: CallContext) -> None:
        super().__init__(
            instructions=build_system_prompt(call_context),
            tools=[
                AppointmentTools(call_context),
                EndCallTool(
                    extra_description="End the call when the customer says goodbye or asks to stop.",
                    end_instructions="End the conversation naturally and briefly.",
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


@server.rtc_session(agent_name="rusborn-voice-agent", on_session_end=on_session_end)
async def entrypoint(ctx: JobContext):
    # Build call context from job metadata or dev env vars
    job_metadata = ctx.job.metadata if hasattr(ctx, "job") and ctx.job else getattr(ctx, "metadata", None)
    
    logger.info(
        "AGENT_JOB_RECEIVED\n"
        f"room={ctx.room.name}\n"
        f"metadata={job_metadata}"
    )
    
    call_context = build_call_context(job_metadata)

    room_name = ctx.room.name
    started_at_str = datetime.utcnow().isoformat()

    logger.info("AGENT_SESSION_STARTED")

    # Check for missing customer context
    if not call_context.has_customer:
        logger.warning(
            f"Missing customer context. Creating call without customer_id for room {room_name}."
        )

    # Idempotent call creation
    db_call = create_or_reuse_call(
        customer_id=call_context.customer_id,
        direction=call_context.direction,
        livekit_room_id=room_name,
        started_at=started_at_str,
        campaign_id=call_context.campaign_id
    )

    if db_call:
        call_context.call_id = db_call.get("id")
    else:
        logger.error(f"Failed to create or reuse database call for room {room_name}. Proceeding without a call_id.")

    logger.info(
        f"Created/reused call:\n"
        f"customer_id={call_context.customer_id}\n"
        f"call_id={call_context.call_id}\n"
        f"room_id={room_name}"
    )

    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="en"),
        stt_context_options={
            "keyterms": [
                "RUSBORN",
                "Rusborn",
                "AI calling",
                "AI voice agent",
                "CRM",
                "CAD",
                "SolidWorks",
                "CATIA",
                "CAE",
                "research mentorship",
                "automation",
                "appointment",
            ],
            "keyterm_detection": {"enabled": True},
        },
        llm=inference.LLM(
            model="google/gemma-4-31b-it",
        ),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="638efaaa-4d0c-442e-b701-3fae16aad012",
            language="en-IN",
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            preemptive_generation={"enabled": True},
            endpointing={"min_delay": 1.0},
        ),
        vad=inference.VAD(),
    )

    @session.on("metrics_collected")
    def on_metrics_collected(metrics):
        metrics_type = getattr(metrics, "type", None)
        if metrics_type == "stt_metrics":
            logger.info(f"[TURN LATENCY] STT finalization duration: {getattr(metrics, 'duration', 0):.2f}s")
        elif metrics_type == "llm_metrics":
            logger.info(f"[TURN LATENCY] LLM TTFT: {getattr(metrics, 'ttft', 0):.2f}s")
            logger.info(f"[TURN LATENCY] LLM generation duration: {getattr(metrics, 'duration', 0):.2f}s")
        elif metrics_type == "tts_metrics":
            logger.info(f"[TURN LATENCY] TTS TTFA: {getattr(metrics, 'ttfb', 0):.2f}s")
            logger.info(f"[TURN LATENCY] TTS generation duration: {getattr(metrics, 'duration', 0):.2f}s")

    await session.start(
        agent=DefaultAgent(call_context),
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
