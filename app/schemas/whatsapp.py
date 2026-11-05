# ==============================================================================
# WhatsApp Agent Data Schemas
# Path: app/schemas/whatsapp.py
# Purpose: Defines data structures for parsing incoming messages from Meta Webhooks
#          and structuring outbound automated conversational responses.
# ==============================================================================

# Typing utilities for nested data structures
from typing import List, Dict, Any, Optional

# BaseModel, Field: Pydantic classes for schema declaration
from pydantic import BaseModel, Field


class WhatsAppIncomingMessage(BaseModel):
    """
    Normalized incoming message received from Meta Cloud API webhook.
    """
    # message_id: Unique Meta message identifier used for deduplication (idempotency)
    message_id: str
    
    # from_number: Sender phone number in international E.164 format (e.g. +201012345678)
    from_number: str
    
    # sender_name: WhatsApp contact display profile name (optional)
    sender_name: Optional[str] = None
    
    # message_type: Message medium ('text', 'audio', or 'image')
    message_type: str = "text"
    
    # text_body: Text content if message_type is 'text'
    text_body: Optional[str] = None
    
    # audio_url: Temporary audio media download URL if message_type is 'audio'
    audio_url: Optional[str] = None
    
    # timestamp: Message epoch Unix timestamp in seconds
    timestamp: Optional[int] = None


class WhatsAppOutgoingResponse(BaseModel):
    """
    Automated outbound response formulated by the AI Agent.
    """
    # recipient_phone: Destination phone number to receive the response
    recipient_phone: str
    
    # reply_text: Formulated response message in localized dialect
    reply_text: str
    
    # requires_human_handover: Boolean flag indicating if human sales rep intervention is needed
    requires_human_handover: bool = False
    
    # handover_summary: Concise brief of customer requirements displayed to the sales agent in CRM
    handover_summary: Optional[str] = None
    
    # extracted_lead_info: Structured customer profile and requirement metadata
    extracted_lead_info: Optional[Dict[str, Any]] = None
