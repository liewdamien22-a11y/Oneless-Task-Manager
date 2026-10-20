"""
Task list widget — left-column task list with filter tabs and a New Task button.

Fires callbacks when the user selects a task or requests a new one.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, List, Optional

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from oneless.models.task import Task

# Palette
_BG = (0.13, 0.13, 0.15, 1)
_SURFACE = (0.18, 0.18, 0.21, 1)
_SELECTED = (0.22, 0.44, 0.69, 0.9)
_TEXT = (0.92, 0.92, 0.94, 1)
_MUTED = (0.55, 0.55, 0.60, 1)
_HIGH = (0.88, 0.42, 0.20, 1)
_MEDIUM = (0.88, 0.78, 0.20, 1)
_LOW = (0.35, 0.75, 0.45, 1)
_COMPLETED_TEXT = (0.45, 0.45, 0.50, 1)
_NEW_BTN = (0.22, 0.44, 0.69, 1)

FILTERS = ["All", "Today", "Upcoming", "Overdue", "Completed"]

_PRIORITY_COLORS = {"high": _HIGH, "medium": _MEDIUM, "low": _LOW}


def _priority_color(priority: str) -> tuple:
    return _PRIORITY_COLORS.get(priority, _MUTED)


class _TaskRow(BoxLayout):
    """
    A single task row.

    Touch handling is done via on_touch_down on the row itself rather than
    an overlaid Button widget — this avoids the size/pos mismatch that made
    clicks unreliable.
    """

    def __init__(self, task: Task, selected: bool,
                 on_select: Callable[[str], None], **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", "54dp")
        kwargs.setdefault("spacing", 6)
        kwargs.setdefault("padding", [8, 4, 8, 4])
        super().__init__(**kwargs)
        self._task = task
        self._selected = selected
        self._on_select = on_select

        self._draw_bg()
        self._build()
        self.bind(pos=self._redraw_bg, size=self._redraw_bg)

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _draw_bg(self):
        with self.canvas.before:
            Color(*(_SELECTED if self._selected else _SURFACE))
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)

    def _redraw_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def _build(self):
        task = self._task
        today = date.today().isoformat()

        # Priority colour strip
        strip = BoxLayout(size_hint_x=None, width="4dp")
        with strip.canvas.before:
            Color(*_priority_color(task.priority))
            strip_rect = Rectangle(pos=strip.pos, size=strip.size)
        strip.bind(
            pos=lambda i, v: setattr(strip_rect, "pos", v),
            size=lambda i, v: setattr(strip_rect, "size", v),
        )
        self.add_widget(strip)

        # Text block
        text_col = BoxLayout(orientation="vertical", spacing=1)

        title_color = _COMPLETED_TEXT if task.completed else _TEXT
        title_lbl = Label(
            text=("[s]" + task.title + "[/s]") if task.completed else task.title,
            font_size="13sp",
            color=title_color,
            halign="left",
            valign="middle",
            markup=True,
            text_size=(None, None),
        )
        title_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        text_col.add_widget(title_lbl)

        # Sub-line: date / category / subtask count
        sub_parts = []
        if task.due_date:
            is_overdue = not task.completed and task.due_date < today
            date_str = task.due_date + (" " + task.due_time if task.due_time else "")
            sub_parts.append(
                ("[color=#d94f4f]⚠ " + date_str + "[/color]") if is_overdue else date_str
            )
        if task.category:
            sub_parts.append(task.category)
        subtask_count = len(task.subtasks)
        if subtask_count:
            done_count = sum(1 for s in task.subtasks if s.completed)
            sub_parts.append(f"{done_count}/{subtask_count} subtasks")

        if sub_parts:
            sub_lbl = Label(
                text="  ·  ".join(sub_parts),
                font_size="11sp",
                color=_MUTED,
                halign="left",
                valign="middle",
                markup=True,
                text_size=(None, None),
            )
            sub_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
            text_col.add_widget(sub_lbl)

        self.add_widget(text_col)

    # ------------------------------------------------------------------
    # Touch — handle on the row directly, no overlay button needed
    # ------------------------------------------------------------------

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._on_select(self._task.id)
            return True
        return super().on_touch_down(touch)


class TaskListWidget(BoxLayout):
    """
    Task list with filter tabs and New Task button.

    Public API:
        refresh(tasks, selected_id)  — repopulate the list
        on_task_selected             — callback(task_id: str)
        on_new_task                  — callback()
        on_filter_changed            — callback(filter_name: str)
    """

    def __init__(
        self,
        on_task_selected: Callable[[str], None] = None,
        on_new_task: Callable[[], None] = None,
        on_filter_changed: Callable[[str], None] = None,
        **kwargs,
    ):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", 0)
        super().__init__(**kwargs)

        self._on_task_selected = on_task_selected or (lambda t: None)
        self._on_new_task = on_new_task or (lambda: None)
        self._on_filter_changed = on_filter_changed or (lambda f: None)

        self._tasks: List[Task] = []
        self._selected_id: Optional[str] = None
        self._active_filter: str = "All"

        self._build_filter_bar()
        self._build_scroll_area()
        self._build_new_task_button()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self, tasks: List[Task], selected_id: Optional[str] = None) -> None:
        self._tasks = tasks
        self._selected_id = selected_id
        self._repopulate()

    def set_active_filter(self, filter_name: str) -> None:
        """Update the highlighted filter tab without firing the callback."""
        self._active_filter = filter_name
        self._rebuild_filter_bar()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_filter_bar(self) -> None:
        self._filter_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="34dp",
            spacing=2, padding=[4, 2, 4, 2],
        )
        self._rebuild_filter_bar()
        self.add_widget(self._filter_bar)

    def _rebuild_filter_bar(self) -> None:
        self._filter_bar.clear_widgets()
        for fname in FILTERS:
            active = (fname == self._active_filter)
            btn = Button(
                text=fname,
                font_size="11sp",
                background_normal="",
                background_color=_SELECTED if active else _SURFACE,
                color=(1, 1, 1, 1) if active else _TEXT,
            )
            btn.bind(on_press=lambda b, f=fname: self._filter_pressed(f))
            self._filter_bar.add_widget(btn)

    def _build_scroll_area(self) -> None:
        self._scroll = ScrollView(size_hint=(1, 1))
        self._list_layout = GridLayout(cols=1, size_hint_y=None, spacing=2)
        self._list_layout.bind(minimum_height=self._list_layout.setter("height"))
        self._scroll.add_widget(self._list_layout)
        self.add_widget(self._scroll)

    def _build_new_task_button(self) -> None:
        btn = Button(
            text="+ New Task",
            font_size="13sp",
            size_hint_y=None, height="40dp",
            background_normal="",
            background_color=_NEW_BTN,
            color=(1, 1, 1, 1),
            bold=True,
        )
        btn.bind(on_press=lambda *_: self._on_new_task())
        self.add_widget(btn)

    def _repopulate(self) -> None:
        self._list_layout.clear_widgets()
        if not self._tasks:
            self._list_layout.add_widget(Label(
                text="No tasks here yet.",
                font_size="13sp",
                color=_MUTED,
                size_hint_y=None,
                height="48dp",
            ))
            return
        for task in self._tasks:
            row = _TaskRow(
                task=task,
                selected=(task.id == self._selected_id),
                on_select=self._on_task_selected,
            )
            self._list_layout.add_widget(row)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _filter_pressed(self, filter_name: str) -> None:
        self._active_filter = filter_name
        self._rebuild_filter_bar()
        self._on_filter_changed(filter_name)
