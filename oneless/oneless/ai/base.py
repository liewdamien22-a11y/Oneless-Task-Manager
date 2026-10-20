"""
Abstract AI provider interface.

All concrete providers (mock, gemini, openai, watsonx) implement AIProvider.
The UI and service layers only import from this module — never from a concrete
provider directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------

@dataclass
class ChatMessage:
    """A single turn in the conversation history."""
    role: str          # "user" | "assistant"
    content: str


# ---------------------------------------------------------------------------
# Tool-call result — returned alongside the assistant reply
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    """
    Represents a task mutation the AI decided to perform.

    name   — one of: create_task, update_task, complete_task, delete_task
    args   — keyword arguments that map directly onto TaskService methods
    result — human-readable outcome filled in after the call is executed
    """
    name: str
    args: Dict[str, Any]
    result: Optional[str] = None


@dataclass
class AIResponse:
    """Everything returned from a single provider.chat() call."""
    text: str                          # assistant reply shown in the sidebar
    tool_calls: List[ToolCall] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class AIProvider(ABC):
    """Abstract base for all AI backends."""

    @abstractmethod
    def chat(
        self,
        history: List[ChatMessage],
        user_message: str,
        task_context: str,
    ) -> AIResponse:
        """
        Send a user message (with history + task context) and return a response.

        history       — previous turns in this session
        user_message  — the new user input
        task_context  — a plain-text summary of current tasks injected as
                        system context so the model knows what tasks exist
        """
