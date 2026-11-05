# ==============================================================================
# WhatsApp Audio Ingestion Helper
# Path: app/modules/whatsapp_agent/audio.py
# Purpose: Downloads voice notes sent by WhatsApp users from Meta Cloud API
#          and feeds the stream to Whisper Large v3 Turbo for speech recognition.
# ==============================================================================

# In-memory byte buffer operations
import io

# Logging module
import logging

# Asynchronous HTTP client for non-blocking media downloads
import httpx

# Application configuration instance
from app.config import settings

# Core Whisper transcription utility
from app.core.audio import transcribe_audio_file

logger = logging.getLogger(__name__)


async def transcribe_whatsapp_voice(audio_url: str) -> str:
    """
    Downloads WhatsApp audio note and transcribes speech into text.
    
    Parameters:
    - audio_url: Temporary download URL provided by Meta Webhook event
    
    Returns:
    - Transcribed speech string in Arabic/English.
    """
    headers = {}
    if settings.WHATSAPP_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"

    # Asynchronous non-blocking download with 30-second timeout
    async with httpx.AsyncClient() as client:
        response = await client.get(audio_url, headers=headers, timeout=30.0)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to download audio from WhatsApp: HTTP {response.status_code}")
        audio_bytes = response.content

    # Transcribe audio bytes directly in memory
    return transcribe_audio_file(
        file_obj=audio_bytes,
        filename="whatsapp_voice.ogg",
        language="ar"
    )
