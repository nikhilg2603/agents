# interruption_handler.py
import logging
import asyncio
from livekit.agents import AgentSession

logger = logging.getLogger("interruption_handler")

async def _handle_transcription_event(evt, session: AgentSession, agent):
    """
    The core async logic for handling a transcription event.
    
    This function is generic and relies on the provided 'agent' object
    to have a method: _is_only_fillers(text: str) -> bool
    """
    text = evt.alternatives[0].text.strip()
    confidence = evt.alternatives[0].confidence or 1.0

    if not text:
        return

    logger.info(f"ASR: '{text}' (conf={confidence:.2f})")

    if session.is_speaking:
        # 1. AGENT IS SPEAKING (INTERRUPTION LOGIC)

        # Ignore low-confidence murmurs
        if confidence < 0.55:
            logger.info("Ignored: low confidence utterance during agent speech.")
            return

        # Call the agent's internal method, which uses its dynamic list
        if agent._is_only_fillers(text):
            logger.info(f"Ignored filler while agent speaking: '{text}'")
            return

        # REAL interruption → stop TTS immediately
        logger.info(f"Real interruption detected → stopping TTS: '{text}'")
        session.interrupt()
        # The session will automatically process this text after interrupting

    else:
        # 2. AGENT IS QUIET (NORMAL INPUT LOGIC)
        # This is a normal user turn. We must manually
        # push the text to the LLM.
        logger.info(f"Agent is quiet, processing input: '{text}'")
        session.push_text_input(text)

def register_interruption_handler(session: AgentSession, agent):
    """
    Registers the custom transcription handler on the agent session.
    
    Args:
        session: The AgentSession object.
        agent: The agent instance. Must expose a `_is_only_fillers(text: str) -> bool` method.
    """
    
    # This is the sync callback required by @session.on
    def _on_transcription_sync(evt):
        # Schedule the async handler to run
        asyncio.create_task(_handle_transcription_event(evt, session, agent))

    # Register the sync callback
    session.on("transcription", _on_transcription_sync)
    logger.info("Custom interruption handler registered.")