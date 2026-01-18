"""
Configuration management using Pydantic Settings.
Loads environment variables and provides typed configuration.
"""

from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Yellowcake API Configuration
    yellowcake_api_key: str
    yellowcake_api_url: str = "https://api.yellowcake.dev/v1/extract-stream"
    force_yellowcake_fallback: bool = False  # Set to TRUE in .env to bypass Yellowcake

    # LLM Service Configuration
    llm_api_key: str = ""  # Your API Key (Groq, Moonshot, etc.)
    llm_model: str = "llama-3.3-70b-versatile"  # Default model
    llm_api_base: str | None = None  # Optional base URL

    # Prompt Storage Paths (Baked via scripts/optimize_prompts.py)
    leetcode_prompt_path: str = "JobScraper/prompts/leetcode_extraction.json"
    interview_prompt_path: str = "JobScraper/prompts/interview_reconstruction.json"

    # API Configuration
    api_title: str = "JobScraper API"
    api_version: str = "1.0.0"
    api_description: str = "AI-powered company research and interview preparation API"

    # Server Configuration
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        # Handle alias for GROQ_API_KEY
        import os

        if not self.llm_api_key or self.llm_api_key == "":
            self.llm_api_key = os.environ.get("GROQ_API_KEY", "")


# Global settings instance - will load from .env file
settings = Settings()  # pyright: ignore[reportCallIssue]
