"""
Pomodoro timer widget.

Separates timer logic (PomodoroTimer) from the Kivy UI (PomodoroWidget)
so the logic can be unit-tested without a display.

Session types
-------------
  focus       — work interval (default 25 min)
  short_break — short rest    (default 5 min)
  long_break  — longer rest   (default 15 min)

After every `long_break_interval` completed focus sessions a long break
is recommended instead of a short one.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

# ---------------------------------------------------------------------------
# Palette (reuse app conventions)
# ---------------------------------------------------------------------------
_BG      = (0.11, 0.11, 0.13, 1)
_SURFACE = (0.17, 0.17, 0.20, 1)
_ACCENT  = (0.22, 0.44, 0.69, 1)
_SUCCESS = (0.22, 0.65, 0.38, 1)
_WARN    = (0.88, 0.78, 0.20, 1)
_DANGER  = (0.75, 0.22, 0.22, 1)
_TEXT    = (0.92, 0.92, 0.94, 1)
_MUTED   = (0.55, 0.55, 0.60, 1)

SESSION_COLORS = {
    "focus":       _ACCENT,
    "short_break": _SUCCESS,
    "long_break":  _WARN,
}

SESSION_LABELS = {
    "focus":       "Focus",
    "short_break": "Short Break",
    "long_break":  "Long Break",
}

DEFAULT_SETTINGS = {
    "focus_minutes":        25,
    "short_break_minutes":  5,
    "long_break_minutes":   15,
    "long_break_interval":  4,
}


def _bg(widget, color):
    with widget.canvas.before:
        Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda i, v: setattr(rect, "pos", v),
                size=lambda i, v: setattr(rect, "size", v))


# ---------------------------------------------------------------------------
# Pure-logic timer (no Kivy dependency)
# ---------------------------------------------------------------------------

class PomodoroTimer:
    """
    Pure-Python timer state machine.

    Callers must drive it by calling tick() periodically (e.g. from a
    Kivy Clock callback).  on_complete is called exactly once when the
    session reaches zero.
    """

    def __init__(
        self,
        settings: Optional[dict] = None,
        on_complete: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._settings = dict(DEFAULT_SETTINGS)
        if settings:
            self._settings.update(settings)

        self._on_complete = on_complete or (lambda session_type: None)

        self._session_type: str = "focus"
        self._remaining: float = self._duration_for("focus")
        self._running: bool = False
        self._completed_focus: int = 0
        self._completed_this_session: bool = False
        self._last_tick: Optional[float] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def session_type(self) -> str:
        return self._session_type

    @property
    def remaining(self) -> float:
        """Remaining seconds (float)."""
        return max(0.0, self._remaining)

    @property
    def running(self) -> bool:
        return self._running

    @property
    def completed_focus_sessions(self) -> int:
        return self._completed_focus

    @property
    def settings(self) -> dict:
        return dict(self._settings)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._completed_this_session = False
            self._last_tick = time.monotonic()

    def pause(self) -> None:
        self._running = False
        self._last_tick = None

    def reset(self) -> None:
        self._running = False
        self._last_tick = None
        self._completed_this_session = False
        self._remaining = self._duration_for(self._session_type)

    def set_session(self, session_type: str) -> None:
        """Switch session type and reset remaining time."""
        if session_type not in ("focus", "short_break", "long_break"):
            raise ValueError(f"Unknown session type: {session_type}")
        self._running = False
        self._last_tick = None
        self._completed_this_session = False
        self._session_type = session_type
        self._remaining = self._duration_for(session_type)

    def update_settings(self, new_settings: dict) -> None:
        """
        Apply new settings.  Does NOT reset an active session — the
        new durations take effect when the next session starts.
        """
        self._settings.update(new_settings)

    def next_session_type(self) -> str:
        """Return what the next recommended session type would be."""
        if self._session_type != "focus":
            return "focus"
        interval = self._settings["long_break_interval"]
        if (self._completed_focus % interval) == 0 and self._completed_focus > 0:
            return "long_break"
        return "short_break"

    def tick(self) -> None:
        """
        Called once per clock tick while running.
        Uses wall-clock delta for robustness.
        """
        if not self._running:
            return

        now = time.monotonic()
        if self._last_tick is None:
            self._last_tick = now
            return

        elapsed = now - self._last_tick
        self._last_tick = now
        self._remaining -= elapsed

        if self._remaining <= 0 and not self._completed_this_session:
            self._remaining = 0.0
            self._running = False
            self._completed_this_session = True
            if self._session_type == "focus":
                self._completed_focus += 1
            self._on_complete(self._session_type)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _duration_for(self, session_type: str) -> float:
        key = {
            "focus":       "focus_minutes",
            "short_break": "short_break_minutes",
            "long_break":  "long_break_minutes",
        }[session_type]
        return float(self._settings[key]) * 60.0


# ---------------------------------------------------------------------------
# Kivy widget
# ---------------------------------------------------------------------------

class PomodoroWidget(BoxLayout):
    """
    Compact Pomodoro timer panel designed to sit inside the AI sidebar.

    Public API
    ----------
    set_task_name(name)          — show/clear the associated task label
    get_settings() -> dict       — retrieve current timer settings
    apply_settings(dict)         — apply persisted settings on startup
    """

    def __init__(self, on_settings_changed: Optional[Callable[[dict], None]] = None, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("spacing", 4)
        kwargs.setdefault("padding", [8, 6, 8, 6])
        super().__init__(**kwargs)
        _bg(self, _BG)

        self._on_settings_changed = on_settings_changed or (lambda s: None)
        self._timer = PomodoroTimer(on_complete=self._on_session_complete)
        self._clock_event = None
        self._settings_visible = False

        self._build()
        self._update_display()
        self.bind(minimum_height=self.setter("height"))

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def set_task_name(self, name: Optional[str]) -> None:
        if name:
            self._task_lbl.text = f"Task: {name}"
            self._task_lbl.color = _TEXT
        else:
            self._task_lbl.text = "No task selected"
            self._task_lbl.color = _MUTED

    def get_settings(self) -> dict:
        return self._timer.settings

    def apply_settings(self, settings: dict) -> None:
        self._timer.update_settings(settings)
        self._update_display()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Section header
        hdr = Label(
            text="Pomodoro Timer",
            font_size="13sp", bold=True, color=_TEXT,
            size_hint_y=None, height="22dp",
            halign="left", valign="middle",
        )
        hdr.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(hdr)

        # Session-type indicator
        self._session_lbl = Label(
            text="", font_size="11sp", color=_ACCENT,
            size_hint_y=None, height="18dp",
            halign="left", valign="middle",
        )
        self._session_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(self._session_lbl)

        # Task association label
        self._task_lbl = Label(
            text="No task selected",
            font_size="11sp", color=_MUTED,
            size_hint_y=None, height="18dp",
            halign="left", valign="middle",
        )
        self._task_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(self._task_lbl)

        # Countdown display
        self._countdown_lbl = Label(
            text="25:00",
            font_size="28sp", bold=True, color=_TEXT,
            size_hint_y=None, height="42dp",
            halign="center", valign="middle",
        )
        self._countdown_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(self._countdown_lbl)

        # Focus-session counter
        self._counter_lbl = Label(
            text="", font_size="11sp", color=_MUTED,
            size_hint_y=None, height="16dp",
            halign="center", valign="middle",
        )
        self._counter_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(self._counter_lbl)

        # Status / notification label
        self._status_lbl = Label(
            text="",
            font_size="11sp", color=_SUCCESS,
            size_hint_y=None, height="18dp",
            halign="center", valign="middle",
        )
        self._status_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(self._status_lbl)

        # Control buttons row
        ctrl = BoxLayout(orientation="horizontal", size_hint_y=None, height="34dp", spacing=4)
        self._btn_start  = self._mk_btn("Start",  _SUCCESS, self._do_start)
        self._btn_pause  = self._mk_btn("Pause",  _WARN,    self._do_pause)
        self._btn_reset  = self._mk_btn("Reset",  _SURFACE, self._do_reset)
        self._btn_settings = self._mk_btn("⚙",   _SURFACE, self._toggle_settings, width="34dp")
        for b in (self._btn_start, self._btn_pause, self._btn_reset, self._btn_settings):
            ctrl.add_widget(b)
        self.add_widget(ctrl)

        # Session-type quick-select row
        sess = BoxLayout(orientation="horizontal", size_hint_y=None, height="28dp", spacing=4)
        for stype, slabel in SESSION_LABELS.items():
            b = Button(
                text=slabel, font_size="10sp",
                background_normal="", background_color=_SURFACE, color=_TEXT,
            )
            b.bind(on_press=lambda _, t=stype: self._switch_session(t))
            sess.add_widget(b)
        self.add_widget(sess)

        # Settings panel (hidden by default)
        self._settings_panel = self._build_settings_panel()
        self._settings_panel.opacity = 0
        self._settings_panel.disabled = True
        self.add_widget(self._settings_panel)

    def _mk_btn(self, text, color, callback, width=None):
        b = Button(
            text=text, font_size="12sp",
            background_normal="", background_color=color, color=(1, 1, 1, 1),
            size_hint_y=None, height="34dp",
        )
        if width:
            b.size_hint_x = None
            b.width = width
        b.bind(on_press=lambda *_: callback())
        return b

    def _build_settings_panel(self) -> BoxLayout:
        panel = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=4, padding=[0, 4, 0, 4],
        )
        panel.bind(minimum_height=panel.setter("height"))

        panel.add_widget(Label(
            text="Timer Settings", font_size="12sp", bold=True, color=_TEXT,
            size_hint_y=None, height="20dp",
            halign="left", valign="middle",
        ))

        fields = [
            ("Focus (min)",        "focus_minutes",       "25"),
            ("Short break (min)",  "short_break_minutes", "5"),
            ("Long break (min)",   "long_break_minutes",  "15"),
            ("Long break after N focus sessions", "long_break_interval", "4"),
        ]
        self._settings_inputs: dict = {}
        for label_text, key, default in fields:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height="30dp", spacing=6)
            row.add_widget(Label(
                text=label_text, font_size="11sp", color=_MUTED,
                halign="left", valign="middle",
            ))
            ti = TextInput(
                text=str(self._timer.settings.get(key, default)),
                multiline=False, font_size="12sp",
                background_color=_SURFACE, foreground_color=_TEXT,
                size_hint_x=None, width="52dp",
                size_hint_y=None, height="28dp",
            )
            self._settings_inputs[key] = ti
            row.add_widget(ti)
            panel.add_widget(row)

        self._settings_error_lbl = Label(
            text="", font_size="10sp", color=_DANGER,
            size_hint_y=None, height="16dp",
            halign="left", valign="middle",
        )
        self._settings_error_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        panel.add_widget(self._settings_error_lbl)

        apply_btn = Button(
            text="Apply", font_size="12sp",
            background_normal="", background_color=_ACCENT, color=(1, 1, 1, 1),
            size_hint_y=None, height="28dp",
        )
        apply_btn.bind(on_press=lambda *_: self._apply_settings())
        panel.add_widget(apply_btn)

        return panel

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def _do_start(self) -> None:
        self._timer.start()
        self._ensure_clock()
        self._update_display()
        self._status_lbl.text = ""

    def _do_pause(self) -> None:
        self._timer.pause()
        self._cancel_clock()
        self._update_display()

    def _do_reset(self) -> None:
        self._timer.reset()
        self._cancel_clock()
        self._update_display()
        self._status_lbl.text = ""

    def _switch_session(self, session_type: str) -> None:
        self._timer.set_session(session_type)
        self._cancel_clock()
        self._update_display()
        self._status_lbl.text = ""

    def _toggle_settings(self) -> None:
        self._settings_visible = not self._settings_visible
        self._settings_panel.opacity = 1 if self._settings_visible else 0
        self._settings_panel.disabled = not self._settings_visible

    def _apply_settings(self) -> None:
        new = {}
        try:
            for key, ti in self._settings_inputs.items():
                val = int(ti.text.strip())
                if val <= 0:
                    raise ValueError(f"{key} must be a positive integer.")
                if key in ("focus_minutes", "short_break_minutes", "long_break_minutes") and val > 180:
                    raise ValueError(f"{key} must be ≤ 180 minutes.")
                if key == "long_break_interval" and val > 20:
                    raise ValueError("Long break interval must be ≤ 20.")
                new[key] = val
        except ValueError as exc:
            self._settings_error_lbl.text = str(exc)
            return

        self._settings_error_lbl.text = ""
        self._timer.update_settings(new)
        self._update_display()
        self._on_settings_changed(self._timer.settings)

    # ------------------------------------------------------------------
    # Clock management
    # ------------------------------------------------------------------

    def _ensure_clock(self) -> None:
        if self._clock_event is None:
            self._clock_event = Clock.schedule_interval(self._tick, 0.25)

    def _cancel_clock(self) -> None:
        if self._clock_event is not None:
            self._clock_event.cancel()
            self._clock_event = None

    def _tick(self, dt) -> None:
        self._timer.tick()
        self._update_display()
        if not self._timer.running:
            self._cancel_clock()

    # ------------------------------------------------------------------
    # Completion callback
    # ------------------------------------------------------------------

    def _on_session_complete(self, session_type: str) -> None:
        self._cancel_clock()
        nxt = self._timer.next_session_type()
        nxt_label = SESSION_LABELS[nxt]
        if session_type == "focus":
            self._status_lbl.text = (
                f"✓ Focus done! ({self._timer.completed_focus_sessions} total)  "
                f"→ {nxt_label} recommended"
            )
        else:
            self._status_lbl.text = f"✓ {SESSION_LABELS[session_type]} complete!  → Focus next"
        self._update_display()

    # ------------------------------------------------------------------
    # Display refresh
    # ------------------------------------------------------------------

    def _update_display(self) -> None:
        remaining = int(self._timer.remaining)
        mins, secs = divmod(remaining, 60)
        self._countdown_lbl.text = f"{mins:02d}:{secs:02d}"

        stype = self._timer.session_type
        self._session_lbl.text = SESSION_LABELS[stype]
        self._session_lbl.color = SESSION_COLORS[stype]
        self._countdown_lbl.color = SESSION_COLORS[stype]

        self._counter_lbl.text = (
            f"Focus sessions completed: {self._timer.completed_focus_sessions}"
        )

        running = self._timer.running
        self._btn_start.disabled  = running
        self._btn_pause.disabled  = not running
        self._btn_start.text = "Resume" if (not running and self._timer.remaining < self._timer._duration_for(stype)) else "Start"
