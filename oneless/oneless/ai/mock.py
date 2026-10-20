"""
Mock AI provider — deterministic responses, no credentials needed.

Used as the default when AI_PROVIDER is not set or is set to "mock".
Useful for development and testing without an API key.
"""
from __future__ import annotations

from typing import List

from oneless.ai.base import AIProvider, AIResponse, ChatMessage


class MockProvider(AIProvider):
    """Returns scripted responses based on simple keyword matching."""

    def chat(
        self,
        history: List[ChatMessage],
        user_message: str,
        task_context: str,
    ) -> AIResponse:
        msg = user_message.lower()

        if any(w in msg for w in ("hello", "hi", "hey")):
            text = "Hi! I'm the OneLess mock assistant. Connect a real AI provider in your .env to enable full task management via chat."
        elif any(w in msg for w in ("task", "list", "show", "what")):
            text = f"Here's what I can see:\n\n{task_context or 'No tasks yet.'}"
        elif any(w in msg for w in ("help", "can you", "how")):
            text = (
                "With a real AI provider connected I can:\n"
                "• Create tasks from natural language\n"
                "• Update task details, priority, or due date\n"
                "• Mark tasks complete\n"
                "• Delete tasks\n\n"
                "Set AI_PROVIDER=gemini and GEMINI_API_KEY in your .env to get started."
            )
        else:
            text = (
                "I'm the mock provider — I don't understand that yet.\n"
                "Set AI_PROVIDER=gemini in your .env to enable real AI responses."
            )

        return AIResponse(text=text)
