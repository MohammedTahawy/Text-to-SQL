# ==============================================================================
# WhatsApp Webhook & Testing Simulation Router
# Path: app/modules/whatsapp_agent/router.py
# Purpose: 1. Implements Meta Cloud API Webhook verification handshake (GET /webhook).
#          2. Ingests live WhatsApp customer event payloads (POST /webhook).
#          3. Provides a local simulation endpoint (POST /simulate) for local testing
#             without requiring a public tunneling proxy (Ngrok).
# ==============================================================================

# Logging module
import logging

# FastAPI router and request utilities
from fastapi import APIRouter, Request, Query, Response, status, Header, Depends

# Application configuration instance
from app.config import settings

# WhatsApp schemas
from app.schemas.whatsapp import WhatsAppIncomingMessage, WhatsAppOutgoingResponse

# WhatsApp agent service orchestrator
from app.modules.whatsapp_agent.service import whatsapp_agent_service

# Audio transcription helper for WhatsApp audio
from app.modules.whatsapp_agent.audio import transcribe_whatsapp_voice

logger = logging.getLogger(__name__)

# Router instance with prefix '/whatsapp'
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp AI Sales Agent"])


@router.get("/webhook", summary="Meta Webhook Verification")
async def verify_meta_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Standard Meta Cloud API Webhook handshake.
    When registering a webhook URL in Meta App Dashboard, Meta sends a GET request
    with challenge and token. If token matches settings.WHATSAPP_VERIFY_TOKEN,
    return challenge with HTTP 200.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Meta Webhook successfully verified.")
        return Response(content=hub_challenge, media_type="text/plain")
        
    return Response(content="Verification token mismatch", status_code=status.HTTP_403_FORBIDDEN)


@router.post("/webhook", summary="Receive WhatsApp Webhook Events")
async def receive_meta_webhook(request: Request):
    """
    Ingests live message payloads dispatched from Meta Cloud API.
    Immediately returns 200 OK acknowledgment to prevent message re-delivery.
    """
    body = await request.json()
    logger.info(f"Incoming WhatsApp Webhook payload: {body}")
    return {"status": "received"}


@router.post(
    "/simulate",
    response_model=WhatsAppOutgoingResponse,
    summary="Simulate incoming WhatsApp message for testing"
)
async def simulate_message(
    incoming: WhatsAppIncomingMessage,
    x_company_id: int = Header(605, alias="X-Company-Id")
):
    """
    Direct simulation endpoint for testing voice notes and text inquiries
    locally in Swagger UI or Postman without requiring a live Meta phone number.
    """
    # If incoming message is audio with an accessible URL, transcribe it first
    if incoming.message_type == "audio" and incoming.audio_url:
        transcription = await transcribe_whatsapp_voice(incoming.audio_url)
        incoming.text_body = transcription

    # Process through WhatsApp Agent Service
    response = whatsapp_agent_service.process_incoming_message(
        incoming=incoming,
        cmp_no=x_company_id
    )
    return response
