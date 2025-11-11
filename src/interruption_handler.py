# src/interruption_handler.py
import logging
import asyncio
from livekit.agents import AgentSession

logger = logging.getLogger("interruption_handler")

async def _handle_transcription_event(evt, session: AgentSession, agent):
    """
    The core async logic for handling a transcription event.
    """
    text = evt.alternatives[0].text.strip()
    confidence = evt.alternatives[0].confidence or 1.0

    if not text:
        return

    logger.debug(f"ASR: '{text}' (conf={confidence:.2f})") # Changed to debug

    if session.is_speaking:
        # 1. AGENT IS SPEAKING (INTERRUPTION LOGIC)

        # Example check from challenge doc 
        if confidence < 0.55:
            logger.info(f"Ignored: low confidence utterance during agent speech: '{text}'")
            return

        # --- MODIFIED: Call is now synchronous (no 'await') ---
        # This is much faster than an LLM call.
        if agent._is_only_fillers(text):
            logger.info(f"Ignored filler (per list): '{text}'")
            return

        # REAL interruption → stop TTS immediately 
        logger.info(f"Real interruption detected → stopping TTS: '{text}'")
        session.interrupt()

    else:
        # 2. AGENT IS QUIET (NORMAL INPUT LOGIC)
        # This is where commands like "add 'haan' to the list"
        # are sent to the main agent, which can now handle them
        # using its function tools. 
        logger.info(f"Agent is quiet, processing input: '{text}'")
        session.push_text_input(text)

def register_interruption_handler(session: AgentSession, agent):
    """
    Registers the custom transcription handler on the agent session.
    """
    
    def _on_transcription_sync(evt):
        asyncio.create_task(_handle_transcription_event(evt, session, agent))

    session.on("transcription", _on_transcription_sync)
    logger.info("Custom (list-based) interruption handler registered.")