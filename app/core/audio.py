# ==============================================================================
# Speech-to-Text & Audio Transcription Module
# Path: app/core/audio.py
# Purpose: Transcribes manager voice notes and WhatsApp customer audio clips
#          using Whisper Large v3 Turbo hosted on Groq, providing sub-second
#          latency and high accuracy across Arabic dialects (Egyptian & Gulf).
# ==============================================================================

# In-memory byte buffer operations
import io

# Logging module
import logging

# Typing utilities
from typing import BinaryIO, Union

# OpenAI client interface used to interact with Whisper audio endpoints
from openai import OpenAI

    # Application settings instance
from app.config import settings
from app.core.llm import groq_concurrency_semaphore

# Logger instance
logger = logging.getLogger(__name__)


def get_whisper_client() -> OpenAI:
    """
    Initializes and returns an audio client configured for Whisper inference.
    Prefers Groq for ultra-low transcription latency (<1s) and low cost.
    """
    if settings.GROQ_API_KEY:
        return OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
            default_headers={"User-Agent": "InfoSas-AI/1.0"}
        )
    elif settings.OPENAI_API_KEY:
        return OpenAI(api_key=settings.OPENAI_API_KEY)
    else:
        raise ValueError("Neither GROQ_API_KEY nor OPENAI_API_KEY is configured for Whisper audio transcription.")


def transcribe_audio_file(
    file_obj: Union[BinaryIO, bytes],
    filename: str = "voice_note.mp3",
    language: str = "ar"
) -> str:
    """
    Transcribes audio bytes or file streams into written Arabic/English text.
    
    Parameters:
    - file_obj: Raw audio bytes or file-like stream object
    - filename: Filename with extension (e.g. voice_note.mp3, audio.ogg) to inform the decoder
    - language: Language hint code ('ar' for Arabic) to maximize dialect recognition
    
    Returns:
    - Transcribed query text as a string
    """
    client = get_whisper_client()
    model_name = "whisper-large-v3-turbo" if settings.GROQ_API_KEY else "whisper-1"

    # Wrap raw bytes in an in-memory BytesIO stream if not already a file-like object
    if isinstance(file_obj, bytes):
        bio = io.BytesIO(file_obj)
        bio.name = filename
        audio_target = bio
    else:
        if not hasattr(file_obj, "name"):
            file_obj.name = filename
        audio_target = file_obj

    try:
        # Submit audio payload to Whisper endpoint with concurrency control
        with groq_concurrency_semaphore:
            transcription = client.audio.transcriptions.create(
                model=model_name,
                file=audio_target,
                language=language,
                temperature=0.0  # 0.0 enforces deterministic transcription without hallucinated words
            )
        text = transcription.text.strip()
        logger.info(f"Whisper transcription successful ({len(text)} chars): '{text}'")
        return text
    except Exception as e:
        logger.error(f"Error in Whisper audio transcription: {e}")
        raise RuntimeError(f"Audio transcription failed: {str(e)}")
