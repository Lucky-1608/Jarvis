"""
Jarvis OS — Centralized Settings.

All configuration is loaded from environment variables (via .env) with
Pydantic Settings.  Import the singleton ``get_settings()`` wherever
you need configuration values.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Root path of the Jarvis project
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Provider-specific settings
# ---------------------------------------------------------------------------
class OpenCodeSettings(BaseSettings):
    """OpenCode AI provider configuration (primary brain)."""

    model_config = SettingsConfigDict(env_prefix="OPENCODE_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://opencode.ai/v1"
    model: str = "gpt-4o-mini"
    timeout: int = 120
    max_retries: int = 3


class OpenRouterSettings(BaseSettings):
    """OpenRouter AI provider configuration (fallback cloud)."""

    model_config = SettingsConfigDict(env_prefix="OPENROUTER_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "nvidia/llama-3.1-nemotron-70b-instruct:free"
    timeout: int = 120
    max_retries: int = 3


class OllamaSettings(BaseSettings):
    """Ollama local AI provider configuration."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_", env_file=".env", extra="ignore")

    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    timeout: int = 300  # local models can be slower
    max_retries: int = 2

class NvidiaNimSettings(BaseSettings):
    """Nvidia NIM provider configuration (high-performance fallback)."""

    model_config = SettingsConfigDict(env_prefix="NVIDIA_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "nvidia/nemotron-4-340b-instruct"
    timeout: int = 120
    max_retries: int = 3


# ---------------------------------------------------------------------------
# Memory settings
# ---------------------------------------------------------------------------
class MemorySettings(BaseSettings):
    """Memory / vector-database configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    chroma_persist_dir: str = str(PROJECT_ROOT / "data" / "chromadb")
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    max_context_memories: int = 10
    max_context_tokens: int = 4000


# ---------------------------------------------------------------------------
# Server settings
# ---------------------------------------------------------------------------
class ServerSettings(BaseSettings):
    """FastAPI server configuration."""

    model_config = SettingsConfigDict(env_prefix="JARVIS_")

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    secret_key: str = "change-this-to-a-random-secret"
    require_auth: bool = False


# ---------------------------------------------------------------------------
# Master settings
# ---------------------------------------------------------------------------
class JarvisSettings(BaseSettings):
    """
    Root settings object that composes all sub-settings.

    Usage::

        from jarvis.config.settings import get_settings
        settings = get_settings()
        print(settings.ai_primary_provider)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- AI routing ---------------------------------------------------------
    ai_primary_provider: Literal["opencode", "openrouter", "ollama", "nvidia"] = "opencode"
    ai_fallback_provider: Literal["opencode", "openrouter", "ollama", "nvidia"] = "ollama"

    # --- Logging ------------------------------------------------------------
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = Field(default="console")

    # --- Sub-settings (composed manually) -----------------------------------
    opencode: OpenCodeSettings = Field(default_factory=OpenCodeSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    nvidia: NvidiaNimSettings = Field(default_factory=NvidiaNimSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    # --- Derived paths ------------------------------------------------------
    @property
    def data_dir(self) -> Path:
        """Root directory for all persistent data."""
        path = PROJECT_ROOT / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def logs_dir(self) -> Path:
        """Directory for log files."""
        path = PROJECT_ROOT / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> JarvisSettings:
    """Return the singleton settings instance."""
    return JarvisSettings()
