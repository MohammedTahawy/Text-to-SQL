# ==============================================================================
# FastAPI Application Entrypoint
# Path: app/main.py
# Purpose: 1. Initializes FastAPI application instance and logging formatters.
#          2. Configures Cross-Origin Resource Sharing (CORS) for Laravel/Vue.js.
#          3. Mounts API routers for Text-to-SQL and WhatsApp Agent.
#          4. Exposes health monitoring endpoint (/health).
# ==============================================================================

# Logging module
import logging

# FastAPI framework core
from fastapi import FastAPI

# CORS middleware to allow cross-origin requests from the Enterprise ERP frontend domain
from fastapi.middleware.cors import CORSMiddleware

# Application settings instance
from app.config import settings

# Natural language reporting router
from app.modules.text_to_sql.router import router as text_to_sql_router

# WhatsApp AI sales agent router
from app.modules.whatsapp_agent.router import router as whatsapp_router

# Centralized logging configuration
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("executive-ai-copilot")

# Initialize FastAPI application with Swagger metadata
app = FastAPI(
    title="Executive ERP AI Copilot Engine",
    description="Production Multi-Tenant AI Engine for Enterprise ERP & CRM: Text-to-SQL Copilot with AST Security Guardrail, Executive Reporting, and WhatsApp Sales Agent - Built by Mohamed Tahawy",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allowed origins (can be restricted to localhost in production)
    allow_credentials=True,       # Allow credentials and cookies
    allow_methods=["*"],          # Allow all HTTP verbs (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],          # Allow all headers including X-AI-API-KEY and X-Company-Id
)

# Mount feature routers under standard /api/v1 prefix
app.include_router(text_to_sql_router, prefix="/api/v1")
app.include_router(whatsapp_router, prefix="/api/v1")


import os
from fastapi.responses import FileResponse

@app.get("/", include_in_schema=False)
@app.get("/demo", include_in_schema=False)
async def serve_demo():
    demo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo_ui.html")
    if os.path.exists(demo_path):
        return FileResponse(demo_path)
    return {"message": "Executive ERP AI Copilot Running. Visit /demo for interactive dashboard or /docs for API documentation."}


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for Docker container probes, Kubernetes liveness probes,
    and uptime monitoring services.
    """
    return {
        "status": "healthy",
        "service": "executive-ai-copilot",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# Standalone entrypoint execution: python -m app.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
