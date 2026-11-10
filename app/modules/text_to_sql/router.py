# ==============================================================================
# Natural Language Reports API Router
# Path: app/modules/text_to_sql/router.py
# Purpose: Exposes HTTP REST endpoints for the InfoSas ERP frontend:
#          1. POST /api/v1/reports/ask       -> Process text-based analytical queries.
#          2. POST /api/v1/reports/ask-voice -> Process voice queries directly from browser/mobile.
# ==============================================================================

from typing import Optional

# FastAPI router and request parameter utilities
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

# Security dependencies
from app.core.security import verify_api_key, get_tenant_context

# Whisper audio transcription helper
from app.core.audio import transcribe_audio_file

# Common response envelope schema
from app.schemas.common import APIResponse

# Request and response schemas for reporting
from app.schemas.text_to_sql import AskQuestionRequest, AskQuestionResponse

# Text-to-SQL business logic service
from app.modules.text_to_sql.service import text_to_sql_service

# Security exception
from app.modules.text_to_sql.guardrails import SQLSecurityException

# Router instance with prefix '/reports'
router = APIRouter(prefix="/reports", tags=["Natural Language Reports (Text-to-SQL)"])


@router.post(
    "/ask",
    response_model=APIResponse[AskQuestionResponse],
    summary="Ask ERP question in natural language text and get table + chart data"
)
async def ask_erp_question(
    request: AskQuestionRequest,
    _auth=Depends(verify_api_key),
    tenant=Depends(get_tenant_context)
):
    """
    Text-based query endpoint.
    Accepts natural language business questions (e.g. 'What are the top 10 selling products this month?'),
    authenticates internal API key, enforces tenant company and branch isolation,
    and returns SQL query results alongside visualization specs.
    """
    try:
        result = text_to_sql_service.ask(
            request=request,
            cmp_no=tenant["cmp_no"],
            brn_no=tenant.get("brn_no")
        )
        return APIResponse(
            success=True,
            message="Report generated successfully",
            data=result
        )
    except SQLSecurityException as se:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security Guardrail Violation: {str(se)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.post(
    "/ask-voice",
    response_model=APIResponse[AskQuestionResponse],
    summary="Ask ERP question via Voice Note (Whisper Audio) and get table + chart data"
)
async def ask_erp_question_voice(
    audio: Optional[UploadFile] = File(None, description="Audio file (mp3, wav, ogg, m4a, webm)"),
    file: Optional[UploadFile] = File(None, description="Alternative alias for audio upload file"),
    language: str = Form("ar", description="Preferred response language ('ar' or 'en')"),
    include_chart: bool = Form(True, description="Whether to generate chart visualization specs"),
    chart_type: Optional[str] = Form(None, description="Optional explicit chart type preference ('bar', 'pie', 'line', 'doughnut')"),
    _auth=Depends(verify_api_key),
    tenant=Depends(get_tenant_context)
):
    """
    Voice-based query endpoint (Executive Voice Copilot).
    Accepts recorded voice audio (from browser microphone or mobile app),
    transcribes speech into Arabic/English text via Whisper Large v3 Turbo,
    and forwards the transcribed prompt to the Text-to-SQL pipeline.
    """
    upload = audio or file
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio payload provided. Send audio via 'audio' or 'file' form field."
        )

    try:
        # Read incoming audio bytes
        audio_bytes = await upload.read()
        
        # Transcribe audio to text
        transcribed_text = transcribe_audio_file(
            file_obj=audio_bytes,
            filename=upload.filename or "voice_note.webm",
            language=language
        )

        if not transcribed_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not detect or transcribe speech in the provided audio file."
            )

        # Wrap transcribed text into a standard question request
        req = AskQuestionRequest(
            question=transcribed_text,
            language=language,
            include_chart=include_chart,
            chart_type=chart_type
        )

        # Process through Text-to-SQL engine
        result = text_to_sql_service.ask(
            request=req,
            cmp_no=tenant["cmp_no"],
            brn_no=tenant.get("brn_no")
        )

        return APIResponse(
            success=True,
            message=f"Voice transcribed and report generated: '{transcribed_text}'",
            data=result
        )
    except SQLSecurityException as se:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security Guardrail Violation: {str(se)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process voice report: {str(e)}"
        )
