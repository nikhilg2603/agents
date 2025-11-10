import logging
import os  # Added os for environment variables
import re  # Added re for punctuation stripping
import asyncio

from dotenv import load_dotenv

# --- MODIFIED IMPORTS ---
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    inference,
    metrics,
    function_tool,  # Added function_tool
    RunContext,       # Added RunContext
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# --- NEW MODULAR IMPORT ---
import interruption_handler

logger = logging.getLogger("agent")

# --- MOVED FROM OLD HANDLER ---
PUNCTUATION = re.compile(r"[,\.?!]")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant. The user is interacting with you via voice, even if you perceive the conversation as text.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )
        
        # This state is owned by the agent
        self.ignored_words = {
            "uh", "umm", "hmm",  # English
            "haan", "acha", "theek hai"  # Hindi
        }
        logger.info(f"Initialized with ignored words: {self.ignored_words}")

    # This method is called by the interruption_handler
    def _is_only_fillers(self, text: str) -> bool:
        """Checks if the text contains only ignored filler words."""
        normalized_text = PUNCTUATION.sub("", text.lower())
        words = [word for word in normalized_text.split() if word]
        return len(words) > 0 and all(w in self.ignored_words for w in words)

    # This tool remains on the agent
    @function_tool
    async def update_ignored_words(self, context: RunContext, words: list[str]):
        """
        Use this tool to update the list of filler words that the agent
        should ignore when it is speaking.
        """
        self.ignored_words = set(w.lower().strip() for w in words)
        logger.info(f"Updated ignored words to: {self.ignored_words}")
        return f"Ignored words have been updated to: {self.ignored_words}"


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Create agent instance FIRST
    agent = Assistant()

    session = AgentSession(
        # --- MODIFIED FOR BONUS 2 (MULTI-LANGUAGE) ---
        stt=inference.STT(model="assemblyai/universal-streaming"),
        
        llm=inference.LLM(model="openai/gpt-4o-mini"),
        
        tts=inference.TTS(
            model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        
        # --- MODIFIED: REMOVED DEFAULT LOGIC ---
        # We removed turn_detection and vad to let our
        # custom handler take full control of interruptions.
        
        preemptive_generation=True,
    )

    # ... (rest of your metrics and shutdown code) ...
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # --- ALL HANDLER LOGIC IS REPLACED BY THIS ONE LINE ---
    interruption_handler.register_interruption_handler(session, agent)

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))