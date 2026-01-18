"""
Configuration management using Pydantic Settings.
Loads environment variables and provides typed configuration.
"""

from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


from app.utils.key_manager import get_key


from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Yellowcake API Configuration
    _yellowcake_api_key: str = ""  # Private field, we use a property
    yellowcake_api_url: str = "https://api.yellowcake.dev/v1/extract-stream"
    force_yellowcake_fallback: bool = False  # Set to TRUE in .env to bypass Yellowcake

    # LLM Service Configuration
    _llm_api_key: str = ""  # Your API Key (Groq, Moonshot, etc.)
    llm_model: str = "llama-3.3-70b-versatile"  # Default model
    llm_api_base: str | None = None  # Optional base URL

    def get_yellowcake_api_key(
        self, session_id: Optional[str] = None, attempt: int = 0
    ) -> str:
        return get_key("YELLOWCAKE_API_KEY", session_id, attempt)

    def get_llm_api_key(
        self, session_id: Optional[str] = None, attempt: int = 0
    ) -> str:
        # Check LLM_SERVICE_API_KEY, LLM_API_KEY and GROQ_API_KEY
        key = get_key("LLM_SERVICE_API_KEY", session_id, attempt)
        if not key:
            key = get_key("LLM_API_KEY", session_id, attempt)
        if not key:
            key = get_key("GROQ_API_KEY", session_id, attempt)
        return key

    @property
    def yellowcake_api_key(self) -> str:
        return self.get_yellowcake_api_key()

    @property
    def llm_api_key(self) -> str:
        return self.get_llm_api_key()

    # Prompt Storage Paths (Baked via scripts/optimize_prompts.py)
    leetcode_prompt_path: str = "JobScraper/prompts/leetcode_extraction.json"
    interview_prompt_path: str = "JobScraper/prompts/interview_reconstruction.json"

    # API Configuration
    api_title: str = "JobScraper API"
    api_version: str = "1.0.0"
    api_description: str = "AI-powered company research and interview preparation API"

    # Rate Limiting
    tpm_limit: int = 10000

    # Server Configuration
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)


# Global settings instance - will load from .env file
settings = Settings()  # pyright: ignore[reportCallIssue]
