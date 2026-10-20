"""
TaskService — application business logic layer.

All task operations used by the UI and (later) the AI tool handlers
go through this service.  It validates inputs, calls the repository,
and returns domain objects.  It never touches Kivy widgets.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from oneless.models.task import Subtask, Task
from oneless.persistence.repository import TaskRepository


VALID_PRIORITIES = {"low", "medium", "high"}
VALID_FILTERS = {"all", "today", "upcoming", "overdue", "completed"}


def _today_iso() -> str:
    return date.today().isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ValidationError(ValueError):
    """Raised when task input fails validation."""


class TaskService:
    """Stateless service that wraps TaskRepository with validation and filtering."""

    def __init__(self, repo: Optional[TaskRepository] = None) -> None:
        self._repo = repo or TaskRepository()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_task_data(
        self,
        title: str,
        priority: str,
        due_date: Optional[str],
        due_time: Optional[str],
    ) -> None:
        if not title or not title.strip():
            raise ValidationError("Task title must not be empty.")
        if priority not in VALID_PRIORITIES:
            raise ValidationError(
                f"Invalid priority '{priority}'. Use: {', '.join(VALID_PRIORITIES)}."
            )
        if due_date is not None:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                raise ValidationError(
                    f"Invalid due_date '{due_date}'. Expected YYYY-MM-DD."
                )
        if due_time is not None:
            try:
                datetime.strptime(due_time, "%H:%M")
            except ValueError:
                raise ValidationError(
                    f"Invalid due_time '{due_time}'. Expected HH:MM."
                )

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    def create_task(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        due_time: Optional[str] = None,
        priority: str = "medium",
        category: str = "",
        estimated_duration: Optional[int] = None,
    ) -> Task:
        self._validate_task_data(title, priority, due_date, due_time)
        task = Task(
            title=title.strip(),
            description=description,
            due_date=due_date,
            due_time=due_time,
            priority=priority,
            category=category,
            estimated_duration=estimated_duration,
        )
        return self._repo.create_task(task)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._repo.get_task(task_id)

    def list_tasks(self) -> List[Task]:
        return self._repo.list_tasks()

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None,      # pass "" to clear
        due_time: Optional[str] = None,      # pass "" to clear
        priority: Optional[str] = None,
        category: Optional[str] = None,
        estimated_duration: Optional[int] = None,
    ) -> Task:
        task = self._repo.get_task(task_id)
        if task is None:
            raise ValidationError(f"Task '{task_id}' not found.")

        if title is not None:
            task.title = title.strip()
        if description is not None:
            task.description = description
        # Empty string means "clear the field"
        if due_date is not None:
            task.due_date = due_date or None
        if due_time is not None:
            task.due_time = due_time or None
        if priority is not None:
            task.priority = priority
        if category is not None:
            task.category = category
        if estimated_duration is not None:
            task.estimated_duration = estimated_duration

        self._validate_task_data(task.title, task.priority, task.due_date, task.due_time)
        return self._repo.update_task(task)

    def delete_task(self, task_id: str) -> bool:
        if self._repo.get_task(task_id) is None:
            raise ValidationError(f"Task '{task_id}' not found.")
        return self._repo.delete_task(task_id)

    def complete_task(self, task_id: str) -> Task:
        task = self._repo.get_task(task_id)
        if task is None:
            raise ValidationError(f"Task '{task_id}' not found.")
        task.completed = True
        return self._repo.update_task(task)

    def reopen_task(self, task_id: str) -> Task:
        task = self._repo.get_task(task_id)
        if task is None:
            raise ValidationError(f"Task '{task_id}' not found.")
        task.completed = False
        return self._repo.update_task(task)

    # ------------------------------------------------------------------
    # Subtask CRUD
    # ------------------------------------------------------------------

    def create_subtask(self, task_id: str, title: str, position: Optional[int] = None) -> Subtask:
        if not title or not title.strip():
            raise ValidationError("Subtask title must not be empty.")
        task = self._repo.get_task(task_id)
        if task is None:
            raise ValidationError(f"Parent task '{task_id}' not found.")
        pos = position if position is not None else len(task.subtasks)
        subtask = Subtask(task_id=task_id, title=title.strip(), position=pos)
        return self._repo.create_subtask(subtask)

    def update_subtask(
        self,
        subtask_id: str,
        title: Optional[str] = None,
        completed: Optional[bool] = None,
        position: Optional[int] = None,
    ) -> Subtask:
        subtask = self._repo.get_subtask(subtask_id)
        if subtask is None:
            raise ValidationError(f"Subtask '{subtask_id}' not found.")
        if title is not None:
            if not title.strip():
                raise ValidationError("Subtask title must not be empty.")
            subtask.title = title.strip()
        if completed is not None:
            subtask.completed = completed
        if position is not None:
            subtask.position = position
        return self._repo.update_subtask(subtask)

    def delete_subtask(self, subtask_id: str) -> bool:
        if self._repo.get_subtask(subtask_id) is None:
            raise ValidationError(f"Subtask '{subtask_id}' not found.")
        return self._repo.delete_subtask(subtask_id)

    def complete_subtask(self, subtask_id: str) -> Subtask:
        return self.update_subtask(subtask_id, completed=True)

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_tasks(self, filter_name: str) -> List[Task]:
        """Return tasks matching a named filter."""
        today = _today_iso()
        all_tasks = self._repo.list_tasks()

        if filter_name == "all":
            return [t for t in all_tasks if not t.completed]
        if filter_name == "today":
            return [
                t for t in all_tasks
                if not t.completed and t.due_date == today
            ]
        if filter_name == "upcoming":
            return [
                t for t in all_tasks
                if not t.completed
                and t.due_date is not None
                and t.due_date > today
            ]
        if filter_name == "overdue":
            return [
                t for t in all_tasks
                if not t.completed
                and t.due_date is not None
                and t.due_date < today
            ]
        if filter_name == "completed":
            return [t for t in all_tasks if t.completed]
        raise ValidationError(
            f"Unknown filter '{filter_name}'. Valid: {', '.join(VALID_FILTERS)}."
        )

    def list_tasks_for_date(self, date_str: str) -> List[Task]:
        return self._repo.list_tasks_for_date_range(date_str, date_str)

    def list_tasks_for_date_range(self, start: str, end: str) -> List[Task]:
        return self._repo.list_tasks_for_date_range(start, end)

    def get_dates_with_tasks(self, year: int, month: int) -> set:
        return self._repo.get_dates_with_tasks(year, month)

    # ------------------------------------------------------------------
    # Convenience: week overview
    # ------------------------------------------------------------------

    def tasks_for_this_week(self) -> List[Task]:
        today = date.today()
        start = today.isoformat()
        end = (today + timedelta(days=6)).isoformat()
        return self._repo.list_tasks_for_date_range(start, end)
