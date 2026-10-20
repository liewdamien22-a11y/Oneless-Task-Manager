"""
SQLite persistence layer.

All database operations are contained here.
No other module should import sqlite3 or issue raw SQL.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from oneless.models.task import Subtask, Task


DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "oneless.db")

_CREATE_TASKS = """
CREATE TABLE IF NOT EXISTS tasks (
    id                TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    description       TEXT NOT NULL DEFAULT '',
    due_date          TEXT,
    due_time          TEXT,
    priority          TEXT NOT NULL DEFAULT 'medium',
    category          TEXT NOT NULL DEFAULT '',
    completed         INTEGER NOT NULL DEFAULT 0,
    estimated_duration INTEGER,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
"""

_CREATE_SUBTASKS = """
CREATE TABLE IF NOT EXISTS subtasks (
    id         TEXT PRIMARY KEY,
    task_id    TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    completed  INTEGER NOT NULL DEFAULT 0,
    position   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_CREATE_IDX_SUBTASKS = """
CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON subtasks (task_id);
"""

_CREATE_IDX_TASKS_DUE = """
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskRepository:
    """All database access for tasks and subtasks."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_schema()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        conn = self._connect()
        conn.executescript(
            _CREATE_TASKS
            + _CREATE_SUBTASKS
            + _CREATE_IDX_SUBTASKS
            + _CREATE_IDX_TASKS_DUE
        )
        conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_to_task(self, row: sqlite3.Row, subtasks: List[Subtask]) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            due_date=row["due_date"],
            due_time=row["due_time"],
            priority=row["priority"] or "medium",
            category=row["category"] or "",
            completed=bool(row["completed"]),
            estimated_duration=row["estimated_duration"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            subtasks=subtasks,
        )

    def _row_to_subtask(self, row: sqlite3.Row) -> Subtask:
        return Subtask(
            id=row["id"],
            task_id=row["task_id"],
            title=row["title"],
            completed=bool(row["completed"]),
            position=row["position"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _fetch_subtasks(self, task_id: str) -> List[Subtask]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY position ASC, created_at ASC",
            (task_id,),
        ).fetchall()
        return [self._row_to_subtask(r) for r in rows]

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    def create_task(self, task: Task) -> Task:
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO tasks
                (id, title, description, due_date, due_time, priority, category,
                 completed, estimated_duration, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id, task.title, task.description, task.due_date,
                task.due_time, task.priority, task.category,
                int(task.completed), task.estimated_duration,
                task.created_at, task.updated_at,
            ),
        )
        conn.commit()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        conn = self._connect()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_task(row, self._fetch_subtasks(task_id))

    def list_tasks(self) -> List[Task]:
        conn = self._connect()
        rows = conn.execute("SELECT * FROM tasks ORDER BY due_date ASC, created_at ASC").fetchall()
        return [self._row_to_task(r, self._fetch_subtasks(r["id"])) for r in rows]

    def update_task(self, task: Task) -> Task:
        task.updated_at = _now_iso()
        conn = self._connect()
        conn.execute(
            """
            UPDATE tasks SET
                title = ?, description = ?, due_date = ?, due_time = ?,
                priority = ?, category = ?, completed = ?,
                estimated_duration = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                task.title, task.description, task.due_date, task.due_time,
                task.priority, task.category, int(task.completed),
                task.estimated_duration, task.updated_at, task.id,
            ),
        )
        conn.commit()
        return task

    def delete_task(self, task_id: str) -> bool:
        conn = self._connect()
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Subtask CRUD
    # ------------------------------------------------------------------

    def create_subtask(self, subtask: Subtask) -> Subtask:
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO subtasks (id, task_id, title, completed, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subtask.id, subtask.task_id, subtask.title,
                int(subtask.completed), subtask.position,
                subtask.created_at, subtask.updated_at,
            ),
        )
        conn.commit()
        return subtask

    def get_subtask(self, subtask_id: str) -> Optional[Subtask]:
        conn = self._connect()
        row = conn.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
        return self._row_to_subtask(row) if row else None

    def update_subtask(self, subtask: Subtask) -> Subtask:
        subtask.updated_at = _now_iso()
        conn = self._connect()
        conn.execute(
            """
            UPDATE subtasks SET title = ?, completed = ?, position = ?, updated_at = ?
            WHERE id = ?
            """,
            (subtask.title, int(subtask.completed), subtask.position,
             subtask.updated_at, subtask.id),
        )
        conn.commit()
        return subtask

    def delete_subtask(self, subtask_id: str) -> bool:
        conn = self._connect()
        cur = conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
        conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Date-range query
    # ------------------------------------------------------------------

    def list_tasks_for_date_range(self, start: str, end: str) -> List[Task]:
        """Return tasks whose due_date falls within [start, end] (ISO dates)."""
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT * FROM tasks
            WHERE due_date IS NOT NULL AND due_date >= ? AND due_date <= ?
            ORDER BY due_date ASC, priority ASC
            """,
            (start, end),
        ).fetchall()
        return [self._row_to_task(r, self._fetch_subtasks(r["id"])) for r in rows]

    def get_dates_with_tasks(self, year: int, month: int) -> set:
        """Return the set of ISO date strings that have at least one task in a month."""
        conn = self._connect()
        prefix = f"{year:04d}-{month:02d}"
        rows = conn.execute(
            "SELECT DISTINCT due_date FROM tasks WHERE due_date LIKE ?",
            (prefix + "%",),
        ).fetchall()
        return {r["due_date"] for r in rows}
