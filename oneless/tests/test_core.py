"""
Tests for the models, persistence, and service layers.
These run without Kivy and verify core task management logic.

Usage:
    python tests/test_core.py
"""
import os
import sys
import tempfile
import unittest

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oneless.models.task import Subtask, Task
from oneless.persistence.repository import TaskRepository
from oneless.services.task_service import TaskService, ValidationError


class TestTaskModel(unittest.TestCase):
    def test_default_values(self):
        t = Task(title="Test")
        self.assertIsNotNone(t.id)
        self.assertEqual(t.priority, "medium")
        self.assertFalse(t.completed)
        self.assertIsNone(t.due_date)

    def test_to_dict_roundtrip(self):
        t = Task(title="Round trip", priority="high", due_date="2025-06-30")
        d = t.to_dict()
        t2 = Task.from_dict(d)
        self.assertEqual(t.id, t2.id)
        self.assertEqual(t.title, t2.title)
        self.assertEqual(t.priority, t2.priority)

    def test_subtask_model(self):
        s = Subtask(task_id="abc", title="Step 1")
        self.assertFalse(s.completed)
        d = s.to_dict()
        s2 = Subtask.from_dict(d)
        self.assertEqual(s.title, s2.title)


class TestRepository(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "test.db")
        self._repo = TaskRepository(db_path=self._db)

    def tearDown(self):
        self._repo.close()

    def test_create_and_retrieve(self):
        t = Task(title="Hello", due_date="2025-07-01")
        self._repo.create_task(t)
        fetched = self._repo.get_task(t.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "Hello")
        self.assertEqual(fetched.due_date, "2025-07-01")

    def test_list_tasks(self):
        self._repo.create_task(Task(title="A"))
        self._repo.create_task(Task(title="B"))
        tasks = self._repo.list_tasks()
        self.assertEqual(len(tasks), 2)

    def test_update_task(self):
        t = Task(title="Original")
        self._repo.create_task(t)
        t.title = "Updated"
        self._repo.update_task(t)
        fetched = self._repo.get_task(t.id)
        self.assertEqual(fetched.title, "Updated")

    def test_delete_task(self):
        t = Task(title="Temporary")
        self._repo.create_task(t)
        self.assertTrue(self._repo.delete_task(t.id))
        self.assertIsNone(self._repo.get_task(t.id))

    def test_subtask_cascade_delete(self):
        t = Task(title="Parent")
        self._repo.create_task(t)
        s = Subtask(task_id=t.id, title="Child")
        self._repo.create_subtask(s)
        # Deleting parent should cascade to subtask
        self._repo.delete_task(t.id)
        self.assertIsNone(self._repo.get_subtask(s.id))

    def test_date_range_query(self):
        self._repo.create_task(Task(title="Past", due_date="2024-01-01"))
        self._repo.create_task(Task(title="Now", due_date="2025-06-15"))
        self._repo.create_task(Task(title="Future", due_date="2026-01-01"))
        results = self._repo.list_tasks_for_date_range("2025-01-01", "2025-12-31")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Now")

    def test_get_dates_with_tasks(self):
        self._repo.create_task(Task(title="T1", due_date="2025-06-10"))
        self._repo.create_task(Task(title="T2", due_date="2025-06-20"))
        self._repo.create_task(Task(title="T3", due_date="2025-07-01"))
        dates = self._repo.get_dates_with_tasks(2025, 6)
        self.assertIn("2025-06-10", dates)
        self.assertIn("2025-06-20", dates)
        self.assertNotIn("2025-07-01", dates)


class TestTaskService(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "svc.db")
        self._repo = TaskRepository(db_path=self._db)
        self._svc = TaskService(repo=self._repo)

    def tearDown(self):
        self._repo.close()

    def test_create_task_validation(self):
        with self.assertRaises(ValidationError):
            self._svc.create_task("")  # empty title

    def test_create_task_bad_priority(self):
        with self.assertRaises(ValidationError):
            self._svc.create_task("X", priority="urgent")

    def test_create_task_bad_date(self):
        with self.assertRaises(ValidationError):
            self._svc.create_task("X", due_date="not-a-date")

    def test_full_task_lifecycle(self):
        task = self._svc.create_task("Buy milk", due_date="2025-08-01", priority="low")
        self.assertFalse(task.completed)
        task = self._svc.complete_task(task.id)
        self.assertTrue(task.completed)
        task = self._svc.reopen_task(task.id)
        self.assertFalse(task.completed)
        self.assertTrue(self._svc.delete_task(task.id))

    def test_subtask_lifecycle(self):
        task = self._svc.create_task("Project")
        st = self._svc.create_subtask(task.id, "Step 1")
        self.assertFalse(st.completed)
        st = self._svc.complete_subtask(st.id)
        self.assertTrue(st.completed)
        self.assertTrue(self._svc.delete_subtask(st.id))

    def test_filters(self):
        from datetime import date, timedelta
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        self._svc.create_task("Today task", due_date=today)
        self._svc.create_task("Overdue task", due_date=yesterday)
        self._svc.create_task("Upcoming task", due_date=tomorrow)
        t_done = self._svc.create_task("Done task", due_date=today)
        self._svc.complete_task(t_done.id)

        self.assertEqual(len(self._svc.filter_tasks("today")), 1)
        self.assertEqual(len(self._svc.filter_tasks("overdue")), 1)
        self.assertEqual(len(self._svc.filter_tasks("upcoming")), 1)
        self.assertEqual(len(self._svc.filter_tasks("completed")), 1)
        self.assertEqual(len(self._svc.filter_tasks("all")), 3)  # excludes completed

    def test_update_task(self):
        task = self._svc.create_task("Old title")
        updated = self._svc.update_task(task.id, title="New title", priority="high")
        self.assertEqual(updated.title, "New title")
        self.assertEqual(updated.priority, "high")

    def test_delete_nonexistent_task(self):
        with self.assertRaises(ValidationError):
            self._svc.delete_task("nonexistent-id")


# ---------------------------------------------------------------------------
# Pomodoro timer logic tests (no Kivy required)
# ---------------------------------------------------------------------------

class TestPomodoroTimer(unittest.TestCase):
    """Tests for PomodoroTimer — pure logic, no Kivy."""

    def _make_timer(self, **settings_overrides):
        from oneless.ui.pomodoro_widget import PomodoroTimer, DEFAULT_SETTINGS
        settings = dict(DEFAULT_SETTINGS)
        settings.update(settings_overrides)
        return PomodoroTimer(settings=settings)

    def test_default_state(self):
        from oneless.ui.pomodoro_widget import DEFAULT_SETTINGS
        t = self._make_timer()
        self.assertEqual(t.session_type, "focus")
        self.assertAlmostEqual(t.remaining, DEFAULT_SETTINGS["focus_minutes"] * 60, delta=1)
        self.assertFalse(t.running)
        self.assertEqual(t.completed_focus_sessions, 0)

    def test_start_and_pause(self):
        t = self._make_timer()
        t.start()
        self.assertTrue(t.running)
        t.pause()
        self.assertFalse(t.running)

    def test_reset_restores_full_duration(self):
        from oneless.ui.pomodoro_widget import DEFAULT_SETTINGS
        t = self._make_timer()
        t.start()
        # Manually reduce remaining
        t._remaining = 100.0
        t.reset()
        self.assertFalse(t.running)
        self.assertAlmostEqual(t.remaining, DEFAULT_SETTINGS["focus_minutes"] * 60, delta=1)

    def test_set_session_changes_type_and_duration(self):
        from oneless.ui.pomodoro_widget import DEFAULT_SETTINGS
        t = self._make_timer()
        t.set_session("short_break")
        self.assertEqual(t.session_type, "short_break")
        self.assertAlmostEqual(t.remaining, DEFAULT_SETTINGS["short_break_minutes"] * 60, delta=1)

    def test_set_session_stops_running_timer(self):
        t = self._make_timer()
        t.start()
        self.assertTrue(t.running)
        t.set_session("long_break")
        self.assertFalse(t.running)

    def test_completion_fires_callback_once(self):
        calls = []
        import time
        from oneless.ui.pomodoro_widget import PomodoroTimer
        t = PomodoroTimer(
            settings={"focus_minutes": 1, "short_break_minutes": 1,
                      "long_break_minutes": 1, "long_break_interval": 4},
            on_complete=lambda s: calls.append(s),
        )
        t.start()
        t._remaining = 0.001          # almost done
        t._last_tick = time.monotonic() - 1.0  # pretend 1s elapsed
        t.tick()                      # should complete
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], "focus")
        # A second tick should NOT fire the callback again
        t.tick()
        self.assertEqual(len(calls), 1)

    def test_focus_session_counter_increments(self):
        import time
        from oneless.ui.pomodoro_widget import PomodoroTimer
        t = PomodoroTimer(
            settings={"focus_minutes": 1, "short_break_minutes": 1,
                      "long_break_minutes": 1, "long_break_interval": 4},
            on_complete=lambda s: None,
        )
        t.start()
        t._remaining = 0.001
        t._last_tick = time.monotonic() - 1.0
        t.tick()
        self.assertEqual(t.completed_focus_sessions, 1)

    def test_next_session_after_focus_is_short_break(self):
        t = self._make_timer(long_break_interval=4)
        # 0 completed focus sessions → next break after first session = short break
        # (counter not yet incremented until completion fires)
        self.assertEqual(t.next_session_type(), "short_break")

    def test_next_session_after_interval_is_long_break(self):
        from oneless.ui.pomodoro_widget import PomodoroTimer
        t = PomodoroTimer(
            settings={"focus_minutes": 1, "short_break_minutes": 1,
                      "long_break_minutes": 1, "long_break_interval": 4},
            on_complete=lambda s: None,
        )
        t._completed_focus = 4   # simulate 4 completed sessions
        self.assertEqual(t.next_session_type(), "long_break")

    def test_update_settings_does_not_reset_active_session(self):
        t = self._make_timer()
        t.start()
        t._remaining = 500.0
        t.update_settings({"focus_minutes": 10})
        # Remaining must be unchanged — new duration only applies to next session
        self.assertAlmostEqual(t._remaining, 500.0, delta=2)

    def test_invalid_session_type_raises(self):
        t = self._make_timer()
        with self.assertRaises(ValueError):
            t.set_session("espresso")


# ---------------------------------------------------------------------------
# Repository settings tests
# ---------------------------------------------------------------------------

class TestRepositorySettings(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mktemp(suffix=".db")
        from oneless.persistence.repository import TaskRepository
        self.repo = TaskRepository(db_path=self._tmp)

    def tearDown(self):
        self.repo.close()
        if os.path.exists(self._tmp):
            os.remove(self._tmp)

    def test_get_missing_setting_returns_default(self):
        self.assertIsNone(self.repo.get_setting("nonexistent"))
        self.assertEqual(self.repo.get_setting("nonexistent", "fallback"), "fallback")

    def test_set_and_get_setting(self):
        self.repo.set_setting("theme", "dark")
        self.assertEqual(self.repo.get_setting("theme"), "dark")

    def test_set_setting_upserts(self):
        self.repo.set_setting("theme", "dark")
        self.repo.set_setting("theme", "light")
        self.assertEqual(self.repo.get_setting("theme"), "light")

    def test_multiple_settings_are_independent(self):
        self.repo.set_setting("focus_minutes", "30")
        self.repo.set_setting("short_break_minutes", "10")
        self.assertEqual(self.repo.get_setting("focus_minutes"), "30")
        self.assertEqual(self.repo.get_setting("short_break_minutes"), "10")

    def test_json_roundtrip_for_pomodoro_settings(self):
        import json
        settings = {"focus_minutes": 30, "short_break_minutes": 8,
                    "long_break_minutes": 20, "long_break_interval": 3}
        self.repo.set_setting("pomodoro_settings", json.dumps(settings))
        restored = json.loads(self.repo.get_setting("pomodoro_settings"))
        self.assertEqual(restored, settings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
