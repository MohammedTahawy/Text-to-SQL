# ==============================================================================
# WhatsApp AI Agent Service Orchestrator
# Path: app/modules/whatsapp_agent/service.py
# Purpose: Executes the autonomous Agent Loop:
#          1. Receives customer message and appends to context.
#          2. Calls LLM with function schemas (AGENT_TOOLS_SCHEMA).
#          3. Executes tool calls dynamically against ERP tables if requested.
#          4. Feeds tool outputs back to LLM for final conversational synthesis.
# ==============================================================================

# JSON serialization
import json

# Logging module
import logging

# Typing utilities
from typing import Dict, Any, List

# OpenAI client interface (Groq/OpenAI compatible)
from openai import OpenAI

# Application settings instance
from app.config import settings

# WhatsApp agent system prompt
from app.modules.whatsapp_agent.prompts import WHATSAPP_SYSTEM_PROMPT

# Function schemas and database tool executor
from app.modules.whatsapp_agent.tools import AGENT_TOOLS_SCHEMA, execute_agent_tool

# WhatsApp message schemas
from app.schemas.whatsapp import WhatsAppIncomingMessage, WhatsAppOutgoingResponse

logger = logging.getLogger(__name__)


class WhatsAppAgentService:
    """
    Autonomous conversational agent service for WhatsApp customer interactions.
    """

    def __init__(self):
        """
        Initializes AI client (preferring Groq for low latency and cost efficiency).
        """
        if settings.GROQ_API_KEY:
            self.client = OpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url=settings.GROQ_BASE_URL,
                default_headers={"User-Agent": "Executive-AI-Copilot/1.0"}
            )
            self.model = settings.GROQ_MODEL
        elif settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
        else:
            self.client = None
            self.model = "gpt-4o-mini"

    def process_incoming_message(
        self,
        incoming: WhatsAppIncomingMessage,
        cmp_no: int
    ) -> WhatsAppOutgoingResponse:
        """
        Executes the agent loop: tool invocation, multi-turn reasoning, and response generation.
        
        Parameters:
        - incoming: Incoming message object containing text, sender phone, and media
        - cmp_no: Company ID for strict tenant isolation
        
        Returns:
        - WhatsAppOutgoingResponse with final reply text and handover status.
        """
        if not self.client:
            raise ValueError("No LLM client configured (GROQ_API_KEY or OPENAI_API_KEY required).")

        user_content = incoming.text_body or "مرحباً"

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": WHATSAPP_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Customer Profile: Phone: {incoming.from_number}, Name: {incoming.sender_name or 'Valued Customer'}\nMessage: {user_content}"
            }
        ]

        # -----------------------------------------------------------------
        # Stage 1: Invoke LLM with Function Calling enabled
        # -----------------------------------------------------------------
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=AGENT_TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.3
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        requires_handover = False
        handover_summary = None

        # -----------------------------------------------------------------
        # Stage 2: Execute requested tools if model decided to call functions
        # -----------------------------------------------------------------
        if tool_calls:
            # Append model's tool intent to conversational history
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                # Check if handover to human sales rep was requested
                if function_name == "create_crm_lead_and_handover":
                    requires_handover = True
                    handover_summary = arguments.get("deal_summary")

                # Execute database tool function
                tool_result = execute_agent_tool(
                    tool_name=function_name,
                    arguments=arguments,
                    cmp_no=cmp_no
                )

                # Return tool output back to model context
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            # -----------------------------------------------------------------
            # Stage 3: Second completion call to synthesize final customer reply
            # -----------------------------------------------------------------
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3
            )
            reply_text = final_response.choices[0].message.content or ""
        else:
            reply_text = response_message.content or ""

        return WhatsAppOutgoingResponse(
            recipient_phone=incoming.from_number,
            reply_text=reply_text,
            requires_human_handover=requires_handover,
            handover_summary=handover_summary
        )


# Centralized singleton instance
whatsapp_agent_service = WhatsAppAgentService()
