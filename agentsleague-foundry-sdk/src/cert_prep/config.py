"""
config.py — Central settings for the CertPrep Multi-Agent System
=================================================================
All configuration is loaded from environment variables / .env file.
Edit .env in place — it ships with commented example values for every variable.

Live mode activates automatically when AZURE_OPENAI_ENDPOINT and
AZURE_OPENAI_API_KEY contain real (non-placeholder) values.

Settings hierarchy
------------------
Settings                          ← master frozen dataclass; import via get_settings()
  ├── AzureOpenAIConfig           AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
  │                               AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION
  ├── AzureFoundryConfig          AZURE_AI_PROJECT_CONNECTION_STRING
  ├── AzureContentSafetyConfig    AZURE_CONTENT_SAFETY_ENDPOINT, AZURE_CONTENT_SAFETY_KEY,
  │                               AZURE_CONTENT_SAFETY_THRESHOLD
  ├── AzureCommConfig             AZURE_COMM_CONNECTION_STRING, AZURE_COMM_SENDER_EMAIL
  ├── McpConfig                   MCP_MSLEARN_URL
  └── AppConfig                   FORCE_MOCK_MODE, APP_PIN, ADMIN_USERNAME, ADMIN_PASSWORD

Usage
-----
    from cert_prep.config import get_settings
    cfg = get_settings()
    if cfg.live_mode:
        client = AzureOpenAI(endpoint=cfg.openai.endpoint, ...)

Each service config exposes an `is_configured` property that detects
unfilled placeholder values such as "<your-key>" so callers never need
to write their own validation logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load .env into os.environ (no-op if already set, safe to call multiple times)
load_dotenv(override=False)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _is_placeholder(value: str) -> bool:
    """Return True if the value looks like an unfilled template placeholder."""
    return not value or "<" in value or value.startswith("your-") or value == "PLACEHOLDER"


# ─── Azure OpenAI ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint:    str
    api_key:     str
    deployment:  str
    api_version: str

    @property
    def is_configured(self) -> bool:
        """True when both endpoint and key are real (non-placeholder) values."""
        return (
            bool(self.endpoint)
            and bool(self.api_key)
            and not _is_placeholder(self.endpoint)
            and not _is_placeholder(self.api_key)
        )


# ─── Azure AI Foundry ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AzureFoundryConfig:
    connection_string: str

    @property
    def is_configured(self) -> bool:
        return bool(self.connection_string) and not _is_placeholder(self.connection_string)


# ─── Azure AI Content Safety ─────────────────────────────────────────────────

@dataclass(frozen=True)
class AzureContentSafetyConfig:
    endpoint:  str
    api_key:   str
    threshold: int  # 0=all, 2=medium+, 4=high only

    @property
    def is_configured(self) -> bool:
        return (
            bool(self.endpoint)
            and bool(self.api_key)
            and not _is_placeholder(self.endpoint)
            and not _is_placeholder(self.api_key)
        )


# ─── Azure Communication Services ────────────────────────────────────────────

@dataclass(frozen=True)
class AzureCommConfig:
    connection_string: str
    sender_email:      str

    @property
    def is_configured(self) -> bool:
        return (
            bool(self.connection_string)
            and bool(self.sender_email)
            and not _is_placeholder(self.connection_string)
            and not _is_placeholder(self.sender_email)
        )


# ─── MS Learn MCP Server ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class McpConfig:
    url: str

    @property
    def is_configured(self) -> bool:
        return bool(self.url) and not _is_placeholder(self.url)


# ─── App-level settings ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class AppConfig:
    force_mock_mode:  bool
    app_pin:          str
    admin_username:   str
    admin_password:   str


# ─── Master settings object ──────────────────────────────────────────────────

@dataclass(frozen=True)
class Settings:
    openai:          AzureOpenAIConfig
    foundry:         AzureFoundryConfig
    content_safety:  AzureContentSafetyConfig
    comm:            AzureCommConfig
    mcp:             McpConfig
    app:             AppConfig

    @property
    def live_mode(self) -> bool:
        """Automatically True when Azure OpenAI creds are real and FORCE_MOCK_MODE is false."""
        return self.openai.is_configured and not self.app.force_mock_mode

    def status_summary(self) -> dict[str, str]:
        """Return a dict of service → status badge for the UI."""
        def badge(ok: bool) -> str:
            return "🟢 Live" if ok else "⚪ Not configured"

        return {
            "Azure OpenAI":           badge(self.openai.is_configured),
            "Azure AI Foundry":       badge(self.foundry.is_configured),
            "Azure Content Safety":   badge(self.content_safety.is_configured),
            "Azure Comm Services":    badge(self.comm.is_configured),
            "MS Learn MCP Server":    badge(self.mcp.is_configured),
        }


def get_settings() -> Settings:
    """Load all configuration from environment variables."""
    _str  = lambda k, d="": os.getenv(k, d).strip()
    _int  = lambda k, d=0: int(os.getenv(k, str(d)) or d)
    _bool = lambda k, d=False: os.getenv(k, str(d)).lower() in ("1", "true", "yes")

    return Settings(
        openai=AzureOpenAIConfig(
            endpoint    = _str("AZURE_OPENAI_ENDPOINT").rstrip("/"),
            api_key     = _str("AZURE_OPENAI_API_KEY"),
            deployment  = _str("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            api_version = _str("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        ),
        foundry=AzureFoundryConfig(
            connection_string = _str("AZURE_AI_PROJECT_CONNECTION_STRING"),
        ),
        content_safety=AzureContentSafetyConfig(
            endpoint  = _str("AZURE_CONTENT_SAFETY_ENDPOINT").rstrip("/"),
            api_key   = _str("AZURE_CONTENT_SAFETY_KEY"),
            threshold = _int("AZURE_CONTENT_SAFETY_THRESHOLD", 2),
        ),
        comm=AzureCommConfig(
            connection_string = _str("AZURE_COMM_CONNECTION_STRING"),
            sender_email      = _str("AZURE_COMM_SENDER_EMAIL"),
        ),
        mcp=McpConfig(
            url = _str("MCP_MSLEARN_URL", "http://localhost:3001"),
        ),
        app=AppConfig(
            force_mock_mode = _bool("FORCE_MOCK_MODE", False),
            app_pin         = _str("APP_PIN", "1234"),
            admin_username  = _str("ADMIN_USERNAME", "admin"),
            admin_password  = _str("ADMIN_PASSWORD", "agents2026"),
        ),
    )


# ─── Backwards-compatibility shim ───────────────────────────────────────────

def get_config() -> AzureOpenAIConfig:
    """Legacy accessor — returns just the OpenAI config block."""
    return get_settings().openai
