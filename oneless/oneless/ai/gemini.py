"""
Google Gemini AI provider using the google-genai SDK.

Uses Gemini function calling so the model can perform task CRUD operations
directly in response to natural-language requests.

Requires:
    pip install google-genai
    GEMINI_API_KEY set in .env
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from oneless.ai.base import AIProvider, AIResponse, ChatMessage, ToolCall

# ---------------------------------------------------------------------------
# Tool (function) definitions sent to Gemini
# ---------------------------------------------------------------------------

_TOOLS = [
    {
        "name": "create_task",
        "description": (
            "Create a new task. Use this when the user asks to add, create, or "
            "schedule a new task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for the task (required).",
                },
                "description": {
                    "type": "string",
                    "description": "Optional longer description.",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format, or omit if none.",
                },
                "due_time": {
                    "type": "string",
                    "description": "Due time in HH:MM (24-hour) format, or omit if none.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Task priority. Defaults to 'medium'.",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category or tag label.",
                },
                "estimated_duration": {
                    "type": "integer",
                    "description": "Estimated duration in minutes, or omit if unknown.",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "update_task",
        "description": (
            "Update one or more fields of an existing task. Use the task_id from "
            "the task context. Only include the fields that need to change."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The UUID of the task to update.",
                },
                "title": {"type": "string"},
                "description": {"type": "string"},
                "due_date": {
                    "type": "string",
                    "description": "New due date (YYYY-MM-DD), or empty string to clear.",
                },
                "due_time": {
                    "type": "string",
                    "description": "New due time (HH:MM), or empty string to clear.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "category": {"type": "string"},
                "estimated_duration": {"type": "integer"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The UUID of the task to mark complete.",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "delete_task",
        "description": "Permanently delete a task.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The UUID of the task to delete.",
                },
            },
            "required": ["task_id"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are OneLess, a helpful personal task management assistant.

You have access to the user's full task list (provided below as context before each message).
You can create, update, complete, and delete tasks on the user's behalf using the provided tools.

Guidelines:
- Always confirm what you did after calling a tool (e.g. "Done! I've created a task called '…'").
- When updating or deleting, use the task_id from the task context — never guess an ID.
- If the user's request is ambiguous (e.g. "delete that task" with no prior context), ask which task they mean.
- Keep replies concise and friendly.
- Today's date is available in the task context header.
"""

# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GeminiProvider(AIProvider):
    """Google Gemini provider with function calling for task CRUD."""

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite") -> None:
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise ImportError(
                "google-genai is not installed. Run: pip install google-genai"
            ) from exc

        self._genai = genai
        self._types = genai_types
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def chat(
        self,
        history: List[ChatMessage],
        user_message: str,
        task_context: str,
    ) -> AIResponse:
        types = self._types

        # Build the full system instruction including today's task context
        system_instruction = (
            _SYSTEM_PROMPT
            + "\n\n--- Current Task Context ---\n"
            + (task_context or "No tasks yet.")
        )

        # Convert history to Gemini Content objects
        contents = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg.content)],
                )
            )

        # Append the new user message
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_message)],
            )
        )

        # Build tool declarations
        tool_declarations = []
        for t in _TOOLS:
            tool_declarations.append(
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=t["parameters"],
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(function_declarations=tool_declarations)],
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )

        # Extract text and any function calls from the response
        reply_text = ""
        tool_calls: List[ToolCall] = []

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    reply_text += part.text
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args: Dict[str, Any] = dict(fc.args) if fc.args else {}
                    tool_calls.append(ToolCall(name=fc.name, args=args))

        return AIResponse(text=reply_text.strip(), tool_calls=tool_calls)
