"""
Calendar widget — month-view calendar.

Shows a grid of day buttons for the current month, navigates
forward/backward, highlights today, and marks dates that have tasks.
Fires an 'on_date_selected' event when the user taps a day.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Callable, Optional, Set

from kivy.graphics import Color, Rectangle
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

# Colours
_BG = (0.13, 0.13, 0.15, 1)
_SURFACE = (0.18, 0.18, 0.21, 1)
_TODAY_BG = (0.22, 0.44, 0.69, 1)
_SELECTED_BG = (0.30, 0.55, 0.80, 1)
_TASK_DOT = (0.95, 0.65, 0.20, 1)
_TEXT = (0.92, 0.92, 0.94, 1)
_MUTED = (0.55, 0.55, 0.60, 1)
_HEADER_BG = (0.16, 0.16, 0.19, 1)

DAY_NAMES = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


class _DayButton(Button):
    """A single day cell in the calendar grid."""

    def __init__(self, day: int, is_today: bool, is_selected: bool,
                 has_task: bool, on_press_cb: Callable, **kwargs):
        super().__init__(
            text=str(day),
            font_size="13sp",
            bold=is_today,
            **kwargs,
        )
        self._is_today = is_today
        self._is_selected = is_selected
        self._has_task = has_task
        self._on_press_cb = on_press_cb
        self._day = day
        self._apply_style()
        self.bind(on_press=lambda *_: self._on_press_cb(self._day))

    def _apply_style(self):
        self.background_normal = ""
        self.background_down = ""
        if self._is_selected:
            self.background_color = _SELECTED_BG
            self.color = (1, 1, 1, 1)
        elif self._is_today:
            self.background_color = _TODAY_BG
            self.color = (1, 1, 1, 1)
        else:
            self.background_color = _SURFACE
            self.color = _TEXT
        # Task indicator dot via canvas (drawn as a small coloured rectangle)
        if self._has_task:
            with self.canvas.after:
                Color(*_TASK_DOT)
                # Will be positioned on size/pos changes
        if self._has_task:
            self.bind(pos=self._draw_dot, size=self._draw_dot)

    def _draw_dot(self, *_):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(*_TASK_DOT)
            dot_size = 5
            x = self.x + self.width / 2 - dot_size / 2
            y = self.y + 4
            Rectangle(pos=(x, y), size=(dot_size, dot_size))


class CalendarWidget(BoxLayout):
    """
    Month-view calendar.

    Public API:
        set_task_dates(dates: Set[str])  — provide ISO dates that have tasks
        select_date(date_str: str)       — programmatically select a date
        on_date_selected                 — event; receives (date_str,)
    """

    def __init__(self, on_date_selected: Callable[[str], None] = None, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", 2)
        super().__init__(**kwargs)

        self._on_date_selected = on_date_selected or (lambda d: None)
        self._task_dates: Set[str] = set()

        today = date.today()
        self._year = today.year
        self._month = today.month
        self._selected_date: Optional[str] = today.isoformat()

        self._build()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def set_task_dates(self, dates: Set[str]) -> None:
        self._task_dates = dates
        self._rebuild()

    def select_date(self, date_str: str) -> None:
        self._selected_date = date_str
        try:
            d = date.fromisoformat(date_str)
            self._year = d.year
            self._month = d.month
        except ValueError:
            pass
        self._rebuild()

    def go_to_today(self) -> None:
        today = date.today()
        self._year = today.year
        self._month = today.month
        self._selected_date = today.isoformat()
        self._rebuild()
        self._on_date_selected(self._selected_date)

    # ------------------------------------------------------------------
    # Build / rebuild
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        self.clear_widgets()
        self._build()

    def _build(self) -> None:
        self._build_nav_header()
        self._build_day_names()
        self._build_day_grid()

    def _build_nav_header(self) -> None:
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height="38dp",
                           spacing=4)
        with header.canvas.before:
            Color(*_HEADER_BG)
            self._header_rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_rect, size=self._update_header_rect)

        btn_prev = Button(
            text="‹", font_size="18sp", size_hint_x=None, width="36dp",
            background_normal="", background_color=_SURFACE, color=_TEXT,
        )
        btn_prev.bind(on_press=lambda *_: self._prev_month())

        month_name = calendar.month_abbr[self._month]
        lbl = Label(
            text=f"{month_name}  {self._year}",
            font_size="14sp", color=_TEXT, bold=True,
        )

        btn_today = Button(
            text="Today", font_size="11sp", size_hint_x=None, width="56dp",
            background_normal="", background_color=_SURFACE, color=_TEXT,
        )
        btn_today.bind(on_press=lambda *_: self.go_to_today())

        btn_next = Button(
            text="›", font_size="18sp", size_hint_x=None, width="36dp",
            background_normal="", background_color=_SURFACE, color=_TEXT,
        )
        btn_next.bind(on_press=lambda *_: self._next_month())

        for w in (btn_prev, lbl, btn_today, btn_next):
            header.add_widget(w)
        self.add_widget(header)

    def _update_header_rect(self, instance, value):
        self._header_rect.pos = instance.pos
        self._header_rect.size = instance.size

    def _build_day_names(self) -> None:
        row = GridLayout(cols=7, size_hint_y=None, height="24dp", spacing=2)
        for name in DAY_NAMES:
            row.add_widget(Label(text=name, font_size="11sp", color=_MUTED))
        self.add_widget(row)

    def _build_day_grid(self) -> None:
        today = date.today()
        cal = calendar.monthcalendar(self._year, self._month)
        rows = len(cal)
        grid = GridLayout(cols=7, spacing=2)

        for week in cal:
            for day in week:
                if day == 0:
                    grid.add_widget(Label(text=""))
                    continue
                iso = f"{self._year:04d}-{self._month:02d}-{day:02d}"
                is_today = (self._year == today.year and
                            self._month == today.month and
                            day == today.day)
                is_sel = (iso == self._selected_date)
                has_task = (iso in self._task_dates)
                btn = _DayButton(
                    day=day,
                    is_today=is_today,
                    is_selected=is_sel,
                    has_task=has_task,
                    on_press_cb=self._day_pressed,
                )
                grid.add_widget(btn)

        self.add_widget(grid)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _prev_month(self) -> None:
        if self._month == 1:
            self._month = 12
            self._year -= 1
        else:
            self._month -= 1
        self._rebuild()

    def _next_month(self) -> None:
        if self._month == 12:
            self._month = 1
            self._year += 1
        else:
            self._month += 1
        self._rebuild()

    def _day_pressed(self, day: int) -> None:
        iso = f"{self._year:04d}-{self._month:02d}-{day:02d}"
        self._selected_date = iso
        self._rebuild()
        self._on_date_selected(iso)
