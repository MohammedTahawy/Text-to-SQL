# ==============================================================================
# Security & Multi-Tenant Isolation Module
# Path: app/core/security.py
# Purpose: 1. Validates internal API keys (X-AI-API-KEY) to ensure only authorized
#             backend clients (Laravel) can invoke the microservice.
#          2. Extracts and enforces tenant isolation headers (X-Company-Id, X-Branch-Id).
# ==============================================================================

# FastAPI security and header extraction utilities
from fastapi import Security, HTTPException, status, Header

# APIKeyHeader: FastAPI built-in security scheme to inspect incoming HTTP headers
from fastapi.security.api_key import APIKeyHeader

# Application configuration instance
from app.config import settings

# Name of the internal secret API key header
API_KEY_NAME = "X-AI-API-KEY"

# Header scheme declaration; auto_error=False allows custom exception formatting
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Authentication Guard Dependency.
    Verifies that incoming requests contain the correct internal service key.
    
    Parameters:
    - api_key: Value extracted from the 'X-AI-API-KEY' header
    
    Raises:
    - HTTPException 401 Unauthorized if key is missing or invalid.
    """
    if not api_key or api_key != settings.AI_SERVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Executive Copilot API Key"
        )
    return api_key


async def get_tenant_context(
    x_company_id: int = Header(None, alias="X-Company-Id", description="Tenant Company Number (Cmp_No), or 0 for All Companies in Lab Mode"),
    x_branch_id: int = Header(None, alias="X-Branch-Id", description="Tenant Branch Number (Brn_No)"),
):
    """
    Multi-Tenant Context Extractor Dependency.
    Extracts and validates company and branch identifiers from HTTP request headers.
    When x_company_id is 0 or omitted (in development/lab mode), it allows cross-company testing.
    """
    if x_company_id is not None and x_company_id < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Company-Id cannot be negative"
        )
        
    return {
        "cmp_no": x_company_id if (x_company_id and x_company_id > 0) else None,
        "brn_no": x_branch_id if (x_branch_id and x_branch_id > 0) else None
    }
