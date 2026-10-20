"""
AI provider factory.

Usage:
    from oneless.ai import get_provider
    provider = get_provider()   # reads AI_PROVIDER + keys from environment
"""
from __future__ import annotations

import os
from typing import Optional

from oneless.ai.base import AIProvider, AIResponse, ChatMessage, ToolCall


def get_provider() -> AIProvider:
    """
    Instantiate and return the configured AI provider.

    Reads environment variables (set via .env):
        AI_PROVIDER     — "mock" (default) | "gemini"
        GEMINI_API_KEY  — required when AI_PROVIDER=gemini
    """
    # Load .env if python-dotenv is available (optional dependency)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    provider_name = os.environ.get("AI_PROVIDER", "mock").lower().strip()

    if provider_name == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "AI_PROVIDER is set to 'gemini' but GEMINI_API_KEY is not set. "
                "Add GEMINI_API_KEY=<your key> to your .env file."
            )
        from oneless.ai.gemini import GeminiProvider
        return GeminiProvider(api_key=api_key)

    if provider_name == "mock":
        from oneless.ai.mock import MockProvider
        return MockProvider()

    raise EnvironmentError(
        f"Unknown AI_PROVIDER '{provider_name}'. Valid values: mock, gemini."
    )


__all__ = ["get_provider", "AIProvider", "AIResponse", "ChatMessage", "ToolCall"]
