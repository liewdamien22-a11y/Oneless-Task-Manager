"""
Task and Subtask dataclasses.

All date/time values are stored and passed as ISO-8601 strings internally.
The persistence and service layers handle conversion to/from Python date objects.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Subtask:
    """A single checklist item belonging to a parent Task."""

    id: str = field(default_factory=_new_id)
    task_id: str = ""
    title: str = ""
    completed: bool = False
    position: int = 0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "completed": self.completed,
            "position": self.position,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Subtask":
        return cls(
            id=data.get("id", _new_id()),
            task_id=data.get("task_id", ""),
            title=data.get("title", ""),
            completed=bool(data.get("completed", False)),
            position=int(data.get("position", 0)),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )


@dataclass
class Task:
    """A single task with optional metadata and subtasks."""

    id: str = field(default_factory=_new_id)
    title: str = ""
    description: str = ""
    due_date: Optional[str] = None       # "YYYY-MM-DD" or None
    due_time: Optional[str] = None       # "HH:MM" or None
    priority: str = "medium"             # "low" | "medium" | "high"
    category: str = ""
    completed: bool = False
    estimated_duration: Optional[int] = None  # minutes
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    subtasks: List[Subtask] = field(default_factory=list)

    # Priority ordering helper
    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date,
            "due_time": self.due_time,
            "priority": self.priority,
            "category": self.category,
            "completed": self.completed,
            "estimated_duration": self.estimated_duration,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "subtasks": [s.to_dict() for s in self.subtasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        subtasks = [
            Subtask.from_dict(s) for s in data.get("subtasks", [])
        ]
        return cls(
            id=data.get("id", _new_id()),
            title=data.get("title", ""),
            description=data.get("description", ""),
            due_date=data.get("due_date"),
            due_time=data.get("due_time"),
            priority=data.get("priority", "medium"),
            category=data.get("category", ""),
            completed=bool(data.get("completed", False)),
            estimated_duration=data.get("estimated_duration"),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
            subtasks=subtasks,
        )
