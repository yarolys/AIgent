"""Configuration management."""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # LLM Settings
    LLM_PROVIDER: Literal["anthropic", "openai"] = os.getenv("LLM_PROVIDER", "anthropic")  # type: ignore
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Model names
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Browser Settings
    USER_DATA_DIR: Path = Path(os.getenv("USER_DATA_DIR", "./profiles/default"))
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "30000"))  # ms
    VIEWPORT_WIDTH: int = int(os.getenv("VIEWPORT_WIDTH", "1280"))
    VIEWPORT_HEIGHT: int = int(os.getenv("VIEWPORT_HEIGHT", "900"))

    # Agent Settings
    MAX_STEPS: int = int(os.getenv("MAX_STEPS", "50"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    QUERY_DOM_LIMIT: int = int(os.getenv("QUERY_DOM_LIMIT", "12"))
    MAX_HISTORY_STEPS: int = int(os.getenv("MAX_HISTORY_STEPS", "10"))

    # Output Settings
    OUTPUT_RUNS_DIR: Path = Path(os.getenv("OUTPUT_RUNS_DIR", "./runs"))

    # Timing
    DEFAULT_WAIT_TIMEOUT: float = float(os.getenv("DEFAULT_WAIT_TIMEOUT", "2.0"))
    ACTION_DELAY: float = float(os.getenv("ACTION_DELAY", "0.5"))

    # Context limits (approximate token counts)
    MAX_OBSERVATION_LENGTH: int = int(os.getenv("MAX_OBSERVATION_LENGTH", "2000"))
    MAX_DOM_TEXT_LENGTH: int = int(os.getenv("MAX_DOM_TEXT_LENGTH", "200"))

    @classmethod
    def get_api_key(cls) -> str:
        """Get the API key for the configured provider."""
        if cls.LLM_PROVIDER == "anthropic":
            if not cls.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set")
            return cls.ANTHROPIC_API_KEY
        else:
            if not cls.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set")
            return cls.OPENAI_API_KEY

    @classmethod
    def get_model_name(cls) -> str:
        """Get the model name for the configured provider."""
        if cls.LLM_PROVIDER == "anthropic":
            return cls.ANTHROPIC_MODEL
        return cls.OPENAI_MODEL

    @classmethod
    def ensure_dirs(cls) -> None:
        """Ensure required directories exist."""
        cls.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_RUNS_DIR.mkdir(parents=True, exist_ok=True)


config = Config()
