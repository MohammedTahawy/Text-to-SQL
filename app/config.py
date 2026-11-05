# ==============================================================================
# Application Configuration Module
# Path: app/config.py
# Purpose: Centralized configuration management using Pydantic Settings.
# Loads environment variables from `.env`, validates data types,
# and provides dynamic connection strings (SQLite for local demo,
# MySQL for production).
# ==============================================================================

# Standard library module to interact with operating system file paths
import os

# Typing utility: Optional means the variable can hold a specific type or be None
from typing import Optional

# BaseSettings: Pydantic base class that auto-loads from environment variables / .env file
# SettingsConfigDict: Configuration dictionary to configure env file path and encoding
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings Data Model.
    Inherits from BaseSettings to read automatically from .env or system environment.
    Provides sane defaults for local development and testing.
    """

    # --- 1. General Runtime Settings ---
    # ENVIRONMENT: Runtime stage ('development', 'staging', or 'production')
    ENVIRONMENT: str = "development"
    
    # DEBUG: When True, verbose error logs and FastAPI Swagger UI (/docs) are enabled
    DEBUG: bool = True
    
    # PORT: Port number on which the FastAPI Uvicorn server listens (default: 8000)
    PORT: int = 8000
    
    # HOST: IP address binding ('0.0.0.0' allows external Docker or local network connections)
    HOST: str = "0.0.0.0"
    
    # AI_SERVICE_API_KEY: Internal shared secret token. Requests originating from Laravel
    # must include this token in the 'X-AI-API-KEY' HTTP header to prevent unauthorized access.
    AI_SERVICE_API_KEY: str = "enterprise_copilot_demo_key_2026"

    # --- 2. LLM Provider Configurations ---
    # DEFAULT_LLM_PROVIDER: Active AI provider ('groq', 'openai', or 'gemini')
    DEFAULT_LLM_PROVIDER: str = "groq"
    
    # Groq Settings (ultra-low latency inference engine)
    GROQ_API_KEY: Optional[str] = None
    # Model used for Text-to-SQL synthesis and business narrative explanation
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    # Groq OpenAI-compatible base URL endpoint
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # OpenAI Settings (fallback / alternate provider)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Google Gemini Settings (optional future provider)
    GEMINI_API_KEY: Optional[str] = None

    # --- 3. Database Configurations ---
    # DB_TYPE: 'sqlite' for immediate out-of-the-box local testing, 'mysql' for production ERP
    DB_TYPE: str = "sqlite"
    # Local SQLite database filename
    SQLITE_PATH: str = "demo_enterprise.db"
    
    # Production MySQL Database Settings (active when DB_TYPE='mysql')
    DB_HOST: str = "127.0.0.1"          # MySQL server host / IP
    DB_PORT: int = 3306                 # Default MySQL port
    DB_NAME: str = "enterprise_erp"        # Enterprise ERP database name
    DB_USER: str = "enterprise_readonly"   # Read-only user for strict security
    DB_PASSWORD: str = "readonly_strong_pass"
    DB_POOL_SIZE: int = 10              # Persistent connection pool size
    DB_MAX_OVERFLOW: int = 20           # Maximum overflow connections during peak spikes

    # --- 4. WhatsApp Business Cloud API Settings ---
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None  # Registered Phone Number ID in Meta Developer portal
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None     # Permanent System User Bearer Token from Meta
    WHATSAPP_VERIFY_TOKEN: str = "enterprise_copilot_whatsapp_webhook_2026"  # Verification token for webhook handshake

    # --- 5. Redis Cache Settings ---
    # Used for semantic caching of frequently asked SQL queries to reduce API costs to $0
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def database_url(self) -> str:
        """
        Dynamic property that constructs the appropriate SQLAlchemy database URI
        based on the selected DB_TYPE (SQLite vs MySQL via PyMySQL).
        """
        # If SQLite is selected, resolve absolute path to demo_enterprise.db
        if self.DB_TYPE.lower() == "sqlite":
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, self.SQLITE_PATH)
            return f"sqlite:///{db_path}"
        
        # If MySQL is selected, return PyMySQL connection string with UTF-8 charset
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # Pydantic configuration: loads variables from .env file with UTF-8 encoding
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore any undeclared environment variables without failing
    )


# Singleton instance of Settings to be imported across all application modules
settings = Settings()
