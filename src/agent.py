# src/agent.py
import logging
import os
import re
import asyncio
from typing import Set

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
    function_tool,  # <-- We MUST have this for the bonus task
    RunContext,
)
from livekit.plugins import noise_cancellation, silero

# --- MODULAR IMPORT ---
import interruption_handler

logger = logging.getLogger("agent")

# We use a simple regex to strip punctuation
PUNCTUATION_REGEX = re.compile(r"[^\w\s]")

load_dotenv(".env.local")


# src/agent.py (Corrected Assistant Class)

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant. The user is interacting with you via voice.
            Your responses are concise and to the point.
            You have tools to manage a list of 'ignored words'.
            When the user asks you to add, remove, or list these words,
            use your tools and then confirm the action was successful.
            For example: 'Okay, I've added 'haan' to the ignored list.'""",
        )
        
        try:
            ignored_words_str = os.environ.get("IGNORED_WORDS", "uh,umm,hmm,haan,okay")
            self.ignored_words: Set[str] = set(ignored_words_str.split(','))
            logger.info(f"Initialized with ignored_words: {self.ignored_words}")
        except Exception as e:
            logger.error(f"Failed to initialize ignored_words: {e}")
            self.ignored_words = set()

    def _is_only_fillers(self, text: str) -> bool:
        """
        Checks if the transcribed text contains ONLY filler words
        from the configurable self.ignored_words set.
        """
        normalized_text = text.lower().strip()
        normalized_text = PUNCTUATION_REGEX.sub("", normalized_text)
        words = normalized_text.split()
        if not words:
            return False
            
        is_filler = all(word in self.ignored_words for word in words)
        
        if is_filler:
            logger.debug(f"Classified '{text}' as filler.")
        else:
            logger.debug(f"Classified '{text}' as non-filler.")
            
        return is_filler

    # --- MODIFIED: Changed to 'async def' ---
    @function_tool
    async def add_ignored_word(self, word: str):
        """Adds a new filler word to the dynamic ignored list."""
        word_lower = word.lower().strip()
        if not word_lower:
            return "Cannot add an empty word."
            
        self.ignored_words.add(word_lower)
        logger.info(f"Dynamically added '{word_lower}' to ignored_words. New set: {self.ignored_words}")
        return f"Okay, I will now ignore '{word_lower}' when I am speaking."

    # --- MODIFIED: Changed to 'async def' ---
    @function_tool
    async def remove_ignored_word(self, word: str):
        """Removes a filler word from the dynamic ignored list."""
        word_lower = word.lower().strip()
        if word_lower in self.ignored_words:
            self.ignored_words.remove(word_lower)
            logger.info(f"Dynamically removed '{word_lower}' from ignored_words. New set: {self.ignored_words}")
            return f"Removed '{word_lower}'. I will no longer ignore it."
        else:
            return f"The word '{word_lower}' was not in the list."

    # --- MODIFIED: Changed to 'async def' ---
    @function_tool
    async def list_ignored_words(self):
        """Lists all words currently in the ignored list."""
        if not self.ignored_words:
            return "The ignored list is currently empty."
        
        word_list = ", ".join(sorted(list(self.ignored_words)))
        logger.info(f"Listing ignored words: {word_list}")
        return f"The current ignored words are: {word_list}"
    
    


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
    # This part of your code was correct
    interruption_handler.register_interruption_handler(session, agent)

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))