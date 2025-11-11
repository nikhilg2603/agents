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

    logger.info(f"ASR: '{text}' (conf={confidence:.2f})")

    if session.is_speaking:
        # 1. AGENT IS SPEAKING (INTERRUPTION LOGIC)

        if confidence < 0.55:
            logger.info("Ignored: low confidence utterance during agent speech.")
            return

        # --- MODIFIED: We now 'await' the agent's decision ---
        if await agent._is_only_fillers(text):
            logger.info(f"Ignored filler (per LLM): '{text}'")
            return

        # REAL interruption → stop TTS immediately
        logger.info(f"Real interruption detected → stopping TTS: '{text}'")
        session.interrupt()

    else:
        # 2. AGENT IS QUIET (NORMAL INPUT LOGIC)
        logger.info(f"Agent is quiet, processing input: '{text}'")
        session.push_text_input(text)

def register_interruption_handler(session: AgentSession, agent):
    """
    Registers the custom transcription handler on the agent session.
    """
    
    def _on_transcription_sync(evt):
        asyncio.create_task(_handle_transcription_event(evt, session, agent))

    session.on("transcription", _on_transcription_sync)
    logger.info("Custom interruption handler registered.")