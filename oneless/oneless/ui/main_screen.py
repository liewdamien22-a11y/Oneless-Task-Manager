"""
Main application screen — three-column layout.

Left:   Calendar + Task list (CalendarWidget + TaskListWidget)
Centre: Task detail / edit panel (TaskDetailWidget)
Right:  AI chat sidebar (AISidebarWidget)
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from oneless.ai import get_provider
from oneless.ai.base import ChatMessage
from oneless.services.task_service import TaskService, ValidationError
from oneless.ui.ai_sidebar_widget import AISidebarWidget
from oneless.ui.calendar_widget import CalendarWidget
from oneless.ui.task_detail_widget import TaskDetailWidget
from oneless.ui.task_list_widget import TaskListWidget

_BG = (0.13, 0.13, 0.15, 1)
_DIVIDER = (0.22, 0.22, 0.26, 1)


def _bg(widget, color):
    with widget.canvas.before:
        Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda i, v: setattr(rect, "pos", v),
                size=lambda i, v: setattr(rect, "size", v))


class MainScreen(BoxLayout):
    """
    Root widget: three-column layout.
    Owns the TaskService instance; all child widgets call back into this
    class for data mutations.
    """

    def __init__(self, service: TaskService, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("spacing", 2)
        super().__init__(**kwargs)
        _bg(self, _BG)

        self._service = service
        self._selected_task_id: Optional[str] = None
        self._active_filter = "all"
        self._selected_date: Optional[str] = date.today().isoformat()

        # AI provider + conversation history
        try:
            self._ai_provider = get_provider()
        except Exception as exc:
            self._ai_provider = None
            self._ai_init_error = str(exc)
        else:
            self._ai_init_error = None
        self._chat_history: List[ChatMessage] = []

        self._build_columns()
        self._restore_pomodoro_settings()
        self._refresh_all()

        # Show provider init error in sidebar if one occurred
        if self._ai_init_error:
            self._ai_sidebar.add_assistant_message(
                f"⚠️ AI provider error: {self._ai_init_error}\n\n"
                "Check your .env file and restart the app."
            )

    # ------------------------------------------------------------------
    # Column assembly
    # ------------------------------------------------------------------

    def _build_columns(self) -> None:
        # ── Left column ────────────────────────────────────────────────
        left = BoxLayout(
            orientation="vertical",
            size_hint_x=0.25,
            spacing=2,
        )
        _bg(left, _BG)

        self._calendar = CalendarWidget(
            on_date_selected=self._on_date_selected,
            size_hint_y=0.42,
        )
        left.add_widget(self._calendar)

        self._task_list = TaskListWidget(
            on_task_selected=self._on_task_selected,
            on_new_task=self._on_new_task,
            on_filter_changed=self._on_filter_changed,
            size_hint_y=0.58,
        )
        left.add_widget(self._task_list)

        # ── Centre column ──────────────────────────────────────────────
        self._task_detail = TaskDetailWidget(
            on_save=self._on_task_save,
            on_delete=self._on_task_delete,
            on_complete=self._on_task_complete,
            on_reopen=self._on_task_reopen,
            on_add_subtask=self._on_add_subtask,
            on_complete_subtask=self._on_complete_subtask,
            on_delete_subtask=self._on_delete_subtask,
            on_create_new=self._on_new_task,
            size_hint_x=0.42,
        )

        # ── Right column ───────────────────────────────────────────────
        self._ai_sidebar = AISidebarWidget(
            on_send=self._on_ai_send,
            on_overwhelmed=self._on_overwhelmed,
            on_pomodoro_settings_changed=self._on_pomodoro_settings_changed,
            size_hint_x=0.33,
        )

        self.add_widget(left)
        self.add_widget(self._task_detail)
        self.add_widget(self._ai_sidebar)

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------

    def _refresh_all(self) -> None:
        """Reload tasks and update all panels."""
        self._refresh_list()
        self._refresh_calendar()
        self._refresh_detail()

    def _refresh_list(self) -> None:
        """Reload task list using the active filter."""
        filter_name = self._active_filter
        try:
            tasks = self._service.filter_tasks(filter_name)
        except ValidationError:
            tasks = self._service.list_tasks()

        # If the selected task is no longer in the visible list (e.g. it was
        # completed and the filter is "all" which hides completed tasks, or it
        # was deleted), clear the selection so the detail panel stays in sync.
        visible_ids = {t.id for t in tasks}
        if self._selected_task_id and self._selected_task_id not in visible_ids:
            self._selected_task_id = None

        self._task_list.refresh(tasks, selected_id=self._selected_task_id)
        # Keep the filter tab highlight in sync
        self._task_list.set_active_filter(self._active_filter.capitalize())

    def _refresh_calendar(self) -> None:
        """Update calendar task-date indicators."""
        cal = self._calendar
        dates = self._service.get_dates_with_tasks(cal._year, cal._month)
        cal.set_task_dates(dates)

    def _refresh_detail(self) -> None:
        """Reload the detail panel for the currently selected task."""
        if self._selected_task_id:
            task = self._service.get_task(self._selected_task_id)
            if task:
                self._task_detail.show_task(task)
            else:
                self._selected_task_id = None
                self._task_detail.show_empty()
        else:
            self._task_detail.show_empty()

    # ------------------------------------------------------------------
    # Calendar callbacks
    # ------------------------------------------------------------------

    def _on_date_selected(self, date_str: str) -> None:
        self._selected_date = date_str
        # Refresh the calendar indicators then reload the list using the
        # current filter — don't hijack the filter the user has chosen.
        # The calendar selection is reflected by the highlighted day cell;
        # the task list continues to show whatever filter is active.
        self._refresh_calendar()
        self._refresh_list()

    # ------------------------------------------------------------------
    # Task list callbacks
    # ------------------------------------------------------------------

    def _on_task_selected(self, task_id: str) -> None:
        self._selected_task_id = task_id
        task = self._service.get_task(task_id)
        if task:
            self._task_detail.show_task(task)
            self._ai_sidebar.set_selected_task(task.title)
        self._refresh_list()

    def _on_new_task(self) -> None:
        self._selected_task_id = None
        self._task_detail.enter_create_mode()
        self._ai_sidebar.set_selected_task(None)
        self._refresh_list()

    def _on_filter_changed(self, filter_name: str) -> None:
        self._active_filter = filter_name.lower()
        self._refresh_list()

    # ------------------------------------------------------------------
    # Task detail callbacks
    # ------------------------------------------------------------------

    def _on_task_save(self, task_id: Optional[str], fields: dict) -> None:
        try:
            if task_id is None:
                # Create new task
                task = self._service.create_task(
                    title=fields["title"],
                    description=fields.get("description", ""),
                    due_date=fields.get("due_date"),
                    due_time=fields.get("due_time"),
                    priority=fields.get("priority", "medium"),
                    category=fields.get("category", ""),
                    estimated_duration=fields.get("estimated_duration"),
                )
                self._selected_task_id = task.id
            else:
                task = self._service.update_task(task_id, **fields)
                self._selected_task_id = task.id
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        self._refresh_all()

    def _on_task_delete(self, task_id: str) -> None:
        try:
            self._service.delete_task(task_id)
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        self._selected_task_id = None
        self._refresh_all()

    def _on_task_complete(self, task_id: str) -> None:
        try:
            self._service.complete_task(task_id)
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        # If the active filter hides completed tasks ("all" does), clear the
        # selection now so _refresh_list doesn't re-select a hidden task.
        if self._active_filter != "completed":
            self._selected_task_id = None
        self._refresh_all()

    def _on_task_reopen(self, task_id: str) -> None:
        try:
            self._service.reopen_task(task_id)
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        # Keep the reopened task selected so the user can see it updated.
        self._refresh_all()

    def _on_add_subtask(self, task_id: str, title: str) -> None:
        try:
            self._service.create_subtask(task_id, title)
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        self._refresh_all()

    def _on_complete_subtask(self, subtask_id: str) -> None:
        try:
            self._service.complete_subtask(subtask_id)
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        self._refresh_all()

    def _on_delete_subtask(self, subtask_id: str) -> None:
        try:
            self._service.delete_subtask(subtask_id)
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        self._refresh_all()

    # ------------------------------------------------------------------
    # AI chat handler
    # ------------------------------------------------------------------

    def _build_task_context(self) -> str:
        """Render all tasks as a plain-text summary for the AI system prompt."""
        from datetime import date as _date
        tasks = self._service.list_tasks()
        today = _date.today().isoformat()
        lines = [f"Today's date: {today}", f"Total tasks: {len(tasks)}", ""]
        for t in tasks:
            status = "✓ completed" if t.completed else "pending"
            due = f"due {t.due_date}" if t.due_date else "no due date"
            time_part = f" at {t.due_time}" if t.due_time else ""
            duration = f", ~{t.estimated_duration}min" if t.estimated_duration else ""
            subtask_summary = (
                f", {len(t.subtasks)} subtask(s)" if t.subtasks else ""
            )
            lines.append(
                f"[{t.id}] {t.title} | {status} | {t.priority} priority | "
                f"{due}{time_part}{duration} | category: {t.category or 'none'}"
                f"{subtask_summary}"
            )
        return "\n".join(lines)

    def _on_ai_send(self, text: str) -> None:
        """Called when the user hits Send in the AI sidebar."""
        if self._ai_provider is None:
            self._ai_sidebar.add_user_message(text)
            self._ai_sidebar.add_assistant_message(
                "⚠️ AI provider is not configured. Check your .env file."
            )
            return

        self._ai_sidebar.add_user_message(text)
        self._ai_sidebar.set_loading(True)

        # Run the API call off the main thread so the UI stays responsive
        import threading
        threading.Thread(
            target=self._ai_worker,
            args=(text,),
            daemon=True,
        ).start()

    def _ai_worker(self, user_message: str) -> None:
        """Background thread: call the AI provider then schedule UI update."""
        try:
            task_context = self._build_task_context()
            response = self._ai_provider.chat(
                history=self._chat_history,
                user_message=user_message,
                task_context=task_context,
            )
        except Exception as exc:
            Clock.schedule_once(
                lambda dt, e=str(exc): self._ai_on_error(e), 0
            )
            return

        Clock.schedule_once(
            lambda dt, r=response, u=user_message: self._ai_on_response(u, r), 0
        )

    def _ai_on_response(self, user_message: str, response) -> None:
        """Main thread: apply tool calls, update history, show reply."""
        from oneless.ai.base import ChatMessage

        # Execute any tool calls the model requested
        tool_results = []
        for tc in response.tool_calls:
            result = self._execute_tool_call(tc)
            tool_results.append(result)

        # Update conversation history
        self._chat_history.append(ChatMessage(role="user", content=user_message))
        self._chat_history.append(ChatMessage(role="assistant", content=response.text))

        # Show the assistant reply (fall back to tool result summary if no text)
        display_text = response.text
        if not display_text and tool_results:
            display_text = "\n".join(tool_results)
        if display_text:
            self._ai_sidebar.add_assistant_message(display_text)

        self._ai_sidebar.set_loading(False)

        # Refresh the UI if any mutations happened
        if response.tool_calls:
            self._refresh_all()

    def _ai_on_error(self, error: str) -> None:
        self._ai_sidebar.add_assistant_message(
            f"⚠️ Error talking to the AI: {error}"
        )
        self._ai_sidebar.set_loading(False)

    def _execute_tool_call(self, tc) -> str:
        """Execute a single tool call from the AI and return a result string."""
        try:
            if tc.name == "create_task":
                task = self._service.create_task(**tc.args)
                return f"Created task: '{task.title}'"

            if tc.name == "update_task":
                task_id = tc.args.pop("task_id")
                task = self._service.update_task(task_id, **tc.args)
                return f"Updated task: '{task.title}'"

            if tc.name == "complete_task":
                task = self._service.complete_task(tc.args["task_id"])
                return f"Completed task: '{task.title}'"

            if tc.name == "delete_task":
                self._service.delete_task(tc.args["task_id"])
                return "Task deleted."

            return f"Unknown tool: {tc.name}"

        except ValidationError as exc:
            return f"Could not execute {tc.name}: {exc}"
        except Exception as exc:
            return f"Error in {tc.name}: {exc}"

    # ------------------------------------------------------------------
    # Overwhelmed handler
    # ------------------------------------------------------------------

    def _on_overwhelmed(self) -> None:
        """Called when the user presses 'I'm Feeling Overwhelmed'."""
        self._ai_sidebar.add_user_message("I'm feeling overwhelmed 😰")
        if self._ai_provider is None:
            self._ai_sidebar.add_assistant_message(
                "⚠️ AI provider is not configured. Check your .env file.\n\n"
                "In the meantime: pick your single highest-priority task and "
                "spend just 10 minutes on it."
            )
            return

        self._ai_sidebar.set_loading(True)
        import threading
        threading.Thread(
            target=self._overwhelmed_worker,
            daemon=True,
        ).start()

    def _overwhelmed_worker(self) -> None:
        """Background thread for the overwhelmed AI call."""
        try:
            task_context = self._build_task_context()
            response = self._ai_provider.chat_overwhelmed(
                history=self._chat_history,
                task_context=task_context,
            )
        except Exception as exc:
            Clock.schedule_once(
                lambda dt, e=str(exc): self._ai_on_error(e), 0
            )
            return
        Clock.schedule_once(
            lambda dt, r=response: self._overwhelmed_on_response(r), 0
        )

    def _overwhelmed_on_response(self, response) -> None:
        """Main thread: show the overwhelmed response (no tool calls)."""
        self._chat_history.append(ChatMessage(
            role="user",
            content="I'm feeling overwhelmed. Can you help me figure out what to focus on?",
        ))
        self._chat_history.append(ChatMessage(role="assistant", content=response.text))
        if response.text:
            self._ai_sidebar.add_assistant_message(response.text)
        self._ai_sidebar.set_loading(False)

    # ------------------------------------------------------------------
    # Pomodoro settings persistence
    # ------------------------------------------------------------------

    def _on_pomodoro_settings_changed(self, settings: dict) -> None:
        """Persist Pomodoro timer settings to the database."""
        import json
        repo = self._service._repo
        repo.set_setting("pomodoro_settings", json.dumps(settings))

    def _restore_pomodoro_settings(self) -> None:
        """Load persisted Pomodoro settings and apply them on startup."""
        import json
        repo = self._service._repo
        raw = repo.get_setting("pomodoro_settings")
        if raw:
            try:
                settings = json.loads(raw)
                self._ai_sidebar.apply_pomodoro_settings(settings)
            except (json.JSONDecodeError, Exception):
                pass  # corrupt data — use defaults

    # ------------------------------------------------------------------
    # Error popup
    # ------------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        from kivy.uix.button import Button as KivyButton
        content = BoxLayout(orientation="vertical", spacing=12, padding=16)
        content.add_widget(Label(text=message, color=(1, 1, 1, 1), font_size="13sp"))
        close_btn = KivyButton(
            text="OK", size_hint_y=None, height="36dp",
            background_normal="", background_color=(0.22, 0.44, 0.69, 1),
        )
        popup = Popup(
            title="Error", content=content,
            size_hint=(0.45, 0.25), auto_dismiss=False,
        )
        close_btn.bind(on_press=lambda *_: popup.dismiss())
        content.add_widget(close_btn)
        popup.open()
