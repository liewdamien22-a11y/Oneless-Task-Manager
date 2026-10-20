"""
Main application screen — three-column layout.

Left:   Calendar + Task list (CalendarWidget + TaskListWidget)
Centre: Task detail / edit panel (TaskDetailWidget)
Right:  AI chat sidebar (AISidebarWidget)
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

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

        self._build_columns()
        self._refresh_all()

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
        self._ai_sidebar = AISidebarWidget(size_hint_x=0.33)

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
        self._refresh_list()

    def _on_new_task(self) -> None:
        self._selected_task_id = None
        self._task_detail.enter_create_mode()
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
