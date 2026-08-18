import logging

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

from agent_core.prompts import SYSTEM_PROMPT
from agent_core.summary import on_session_end

logger = logging.getLogger("agent-rusborn-voice-agent")


class DefaultAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
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

@server.rtc_session(agent_name="rusborn-voice-agent", on_session_end=on_session_end)
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
