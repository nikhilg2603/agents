# src/agent.py
import logging
import os
import re
import asyncio

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
    cli,
    inference,
    metrics,
    function_tool,  # We still keep this for other tools
    RunContext,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# --- MODULAR IMPORT ---
import interruption_handler

logger = logging.getLogger("agent")

# We don't need the PUNCTUATION regex anymore,
# the LLM is smart enough to handle it.

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant. The user is interacting with you via voice, even if you perceive the conversation as text.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )
        
        # --- MODIFIED: Agent has its own LLM for internal logic ---
        # This is separate from the main chat LLM and is used
        # only for our filler-word check.
        try:
            self.filler_llm = inference.LLM(model="openai/gpt-4o-mini")
            logger.info("Filler-check LLM initialized (gpt-4o-mini).")
        except Exception as e:
            logger.error(f"Failed to initialize filler-check LLM: {e}")
            logger.error("The agent will NOT be able to ignore fillers.")
            self.filler_llm = None
            
        self.filler_check_prompt = (
            "You are an expert linguistic classifier. The user has said something "
            "while an agent was speaking. Your task is to determine if this speech "
            "is *only* a filler phrase (like 'umm', 'euh', 'haan', 'like', 'you know', etc.) "
            "and contains no substantive content, command, or question. "
            "Answer with a single word: YES or NO.\n\n"
            "Speech: \"{text}\"\n"
            "Classification:"
        )


    # --- MODIFIED: This method is now async and uses an LLM ---
    async def _is_only_fillers(self, text: str) -> bool:
        """
        Uses an LLM to dynamically classify if a text is
        only a filler phrase in any language.
        """
        if not self.filler_llm:
            logger.warning("No filler-check LLM available. Defaulting to NOT filler.")
            return False # Fail safe: if LLM is broken, allow interruptions
            
        prompt = self.filler_check_prompt.format(text=text)
        
        try:
            # Create a new, isolated chat session for this check
            chat = self.filler_llm.chat()
            resp = await chat.a_send_message(prompt)
            answer = await resp.a_text()
            
            answer = answer.strip().upper()
            logger.info(f"Filler check for '{text}': LLM answered '{answer}'")
            return answer == "YES"
        except Exception as e:
            logger.error(f"Filler check LLM call failed: {e}")
            return False # Fail safe: allow interruption if check fails

    # --- REMOVED ---
    # The add/remove/set tools are no longer needed
    # as the LLM handles all languages automatically.
    # You can still add other, unrelated tools here (like `lookup_weather`).


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Create agent instance FIRST
    agent = Assistant()

    session = AgentSession(
        # STT (Multi-language)
        stt=inference.STT(model="assemblyai/universal-streaming"),
        
        # Main Chat LLM
        llm=inference.LLM(model="openai/gpt-4o-mini"),
        
        # TTS (Multi-language)
        tts=inference.TTS(model="cartesia/sonic-3"),
        
        # Removed turn_detection and vad
        preemptive_generation=True,
    )

    # --- METRICS AND USAGE (Unchanged) ---
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)
    # --- END METRICS ---

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # --- Register our modular handler ---
    interruption_handler.register_interruption_handler(session, agent)

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))