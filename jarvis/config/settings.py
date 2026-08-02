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


class OllamaSettings(BaseSettings):
    """Ollama local AI provider configuration."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_", env_file=".env", extra="ignore")

    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    timeout: int = 300  # local models can be slower
    max_retries: int = 2

class OllamaCloudSettings(BaseSettings):
    """Ollama Cloud AI provider configuration."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_CLOUD_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://ollama.com"
    model: str = "minimax-m3:cloud"
    timeout: int = 300
    max_retries: int = 3

class NvidiaNimSettings(BaseSettings):
    """Nvidia NIM provider configuration (high-performance fallback)."""

    model_config = SettingsConfigDict(env_prefix="NVIDIA_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "nvidia/nemotron-4-340b-instruct"
    timeout: int = 120
    max_retries: int = 3


class GrokSettings(BaseSettings):
    """Grok (xAI) provider configuration (cloud fallback)."""

    model_config = SettingsConfigDict(env_prefix="GROK_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://api.x.ai/v1"
    model: str = "grok-3-mini"
    timeout: int = 120
    max_retries: int = 3


class GeminiSettings(BaseSettings):
    """Google Gemini provider configuration (cloud fallback)."""

    model_config = SettingsConfigDict(env_prefix="GEMINI_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    model: str = "gemini-2.5-flash"
    timeout: int = 120
    max_retries: int = 3


class FishAudioSettings(BaseSettings):
    """Fish Audio configuration for TTS and STT."""

    model_config = SettingsConfigDict(env_prefix="FISH_AUDIO_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://api.fish.audio"
    tts_model: str = "s2.1-pro-free"
    asr_model: str = "asr-1-pro" # not sure of exact asr model, standard endpoint might not need it or we can leave empty
    timeout: int = 120
    max_retries: int = 3


class ElevenLabsSettings(BaseSettings):
    """ElevenLabs configuration for TTS."""

    model_config = SettingsConfigDict(env_prefix="ELEVENLABS_", env_file=".env", extra="ignore")

    api_key: str = ""
    base_url: str = "https://api.elevenlabs.io"
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel (default)
    model: str = "eleven_multilingual_v2"
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
    graphify_enabled: bool = True
    graphify_data_dir: str = str(PROJECT_ROOT / "data" / "graphify")
    graphify_auto_rebuild: bool = False
    graphify_max_context_entities: int = 5


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
    ai_primary_provider: str = "ollama_cloud"
    ai_fallback_providers: str = "opencode,nvidia,grok,gemini,ollama"
    ai_tool_selector_enabled: bool = True

    # --- Voice routing ------------------------------------------------------
    tts_provider: str = "elevenlabs"  # elevenlabs | fish_audio | edge_tts
    stt_provider: str = "elevenlabs"  # elevenlabs | fish_audio | azure

    # --- Logging ------------------------------------------------------------
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = Field(default="console")

    # --- Sub-settings (composed manually) -----------------------------------
    opencode: OpenCodeSettings = Field(default_factory=OpenCodeSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    ollama_cloud: OllamaCloudSettings = Field(default_factory=OllamaCloudSettings)
    nvidia: NvidiaNimSettings = Field(default_factory=NvidiaNimSettings)
    grok: GrokSettings = Field(default_factory=GrokSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    fish_audio: FishAudioSettings = Field(default_factory=FishAudioSettings)
    elevenlabs: ElevenLabsSettings = Field(default_factory=ElevenLabsSettings)
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
