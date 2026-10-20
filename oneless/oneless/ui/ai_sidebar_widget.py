"""
AI assistant sidebar — right column.

Contains:
  - AI chat history + input (existing)
  - "I'm Feeling Overwhelmed" button (Feature A)
  - Pomodoro timer panel (Feature B)
  - Focus Music placeholder (Feature C)
"""
from __future__ import annotations

from typing import Callable, Optional

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from oneless.ui.music_placeholder import MusicPlaceholderWidget
from oneless.ui.pomodoro_widget import PomodoroWidget

_BG           = (0.11, 0.11, 0.13, 1)
_SURFACE      = (0.17, 0.17, 0.20, 1)
_ACCENT       = (0.22, 0.44, 0.69, 1)
_TEXT         = (0.92, 0.92, 0.94, 1)
_MUTED        = (0.55, 0.55, 0.60, 1)
_USER_BUBBLE  = (0.22, 0.44, 0.69, 0.85)
_AI_BUBBLE    = (0.22, 0.22, 0.27, 1)
_OVERWHELMED  = (0.65, 0.30, 0.75, 1)   # soft purple — distinct but not alarming
_DIVIDER      = (0.22, 0.22, 0.26, 1)


def _bg(widget, color):
    with widget.canvas.before:
        Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda i, v: setattr(rect, "pos", v),
                size=lambda i, v: setattr(rect, "size", v))


class _Bubble(BoxLayout):
    """Chat message bubble."""

    def __init__(self, text: str, is_user: bool, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("padding", [10, 6, 10, 6])
        super().__init__(**kwargs)
        _bg(self, _USER_BUBBLE if is_user else _AI_BUBBLE)

        lbl = Label(
            text=text,
            font_size="13sp",
            color=_TEXT,
            halign="right" if is_user else "left",
            valign="top",
            size_hint_y=None,
            markup=True,
        )
        lbl.bind(
            size=lambda i, v: setattr(i, "text_size", (v[0], None)),
            texture_size=lambda i, v: setattr(i, "height", v[1] + 4),
        )
        self.add_widget(lbl)
        self.bind(minimum_height=self.setter("height"))


class AISidebarWidget(BoxLayout):
    """
    Right-column AI chat sidebar.

    Accepts:
        on_send(text)       — called when the user submits a chat message
        on_overwhelmed()    — called when the overwhelmed button is pressed
        on_pomodoro_settings_changed(settings: dict) — called when timer
                              settings are applied (for persistence)
    """

    def __init__(
        self,
        on_send: Optional[Callable[[str], None]] = None,
        on_overwhelmed: Optional[Callable[[], None]] = None,
        on_pomodoro_settings_changed: Optional[Callable[[dict], None]] = None,
        **kwargs,
    ):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", 0)
        super().__init__(**kwargs)

        self._on_send = on_send or self._default_send
        self._on_overwhelmed = on_overwhelmed or self._default_overwhelmed
        self._on_pomodoro_settings_changed = on_pomodoro_settings_changed or (lambda s: None)

        _bg(self, _BG)

        self._build_header()
        self._build_history()
        self._build_overwhelmed_button()
        self._build_input_bar()
        self._build_divider()
        self._build_pomodoro()
        self._build_music_placeholder()

        # Welcome message
        self._add_message(
            "Hi! I'm your OneLess AI assistant.\n\n"
            "You can ask me to create, update, complete, or delete tasks using "
            "plain English — for example:\n"
            "• \"Add a task to buy groceries tomorrow\"\n"
            "• \"Mark the dentist task as done\"\n"
            "• \"Change the priority of my report task to high\"",
            is_user=False,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_user_message(self, text: str) -> None:
        self._add_message(text, is_user=True)

    def add_assistant_message(self, text: str) -> None:
        self._add_message(text, is_user=False)

    def set_loading(self, loading: bool) -> None:
        self._send_btn.disabled = loading
        self._send_btn.text = "…" if loading else "Send"
        self._overwhelmed_btn.disabled = loading

    def set_selected_task(self, task_name: Optional[str]) -> None:
        """Notify the Pomodoro timer which task is currently selected."""
        self._pomodoro.set_task_name(task_name)

    def apply_pomodoro_settings(self, settings: dict) -> None:
        """Restore persisted timer settings on startup."""
        self._pomodoro.apply_settings(settings)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="38dp",
            padding=[12, 6, 12, 6],
        )
        _bg(header, _SURFACE)
        lbl = Label(
            text="AI Assistant",
            font_size="14sp", color=_TEXT, bold=True,
            halign="left", valign="middle",
        )
        lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        header.add_widget(lbl)
        self.add_widget(header)

    def _build_history(self) -> None:
        self._scroll = ScrollView(size_hint=(1, 1))
        self._history = GridLayout(
            cols=1, size_hint_y=None, spacing=4, padding=[6, 6, 6, 6],
        )
        self._history.bind(minimum_height=self._history.setter("height"))
        self._scroll.add_widget(self._history)
        self.add_widget(self._scroll)

    def _build_overwhelmed_button(self) -> None:
        """'I'm Feeling Overwhelmed' button — Feature A."""
        self._overwhelmed_btn = Button(
            text="😰  I'm Feeling Overwhelmed",
            font_size="12sp",
            size_hint_y=None, height="38dp",
            background_normal="",
            background_color=_OVERWHELMED,
            color=(1, 1, 1, 1),
            bold=False,
        )
        self._overwhelmed_btn.bind(on_press=lambda *_: self._do_overwhelmed())
        self.add_widget(self._overwhelmed_btn)

    def _build_input_bar(self) -> None:
        bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="48dp",
            spacing=6, padding=[8, 6, 8, 6],
        )
        _bg(bar, _SURFACE)

        self._input = TextInput(
            hint_text="Ask me anything about your tasks…",
            multiline=False,
            font_size="13sp",
            background_color=_BG,
            foreground_color=_TEXT,
            cursor_color=_TEXT,
            hint_text_color=list(_MUTED),
            size_hint_y=None,
            height="36dp",
        )
        self._input.bind(on_text_validate=lambda *_: self._do_send())

        self._send_btn = Button(
            text="Send",
            font_size="12sp",
            size_hint_x=None, width="60dp",
            background_normal="",
            background_color=_ACCENT,
            color=(1, 1, 1, 1),
            size_hint_y=None, height="36dp",
        )
        self._send_btn.bind(on_press=lambda *_: self._do_send())

        bar.add_widget(self._input)
        bar.add_widget(self._send_btn)
        self.add_widget(bar)

    def _build_divider(self) -> None:
        div = BoxLayout(size_hint_y=None, height="2dp")
        _bg(div, _DIVIDER)
        self.add_widget(div)

    def _build_pomodoro(self) -> None:
        """Pomodoro timer panel — Feature B."""
        self._pomodoro = PomodoroWidget(
            on_settings_changed=self._on_pomodoro_settings_changed,
        )
        self.add_widget(self._pomodoro)

    def _build_music_placeholder(self) -> None:
        """Focus music placeholder — Feature C."""
        self.add_widget(MusicPlaceholderWidget())

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _add_message(self, text: str, is_user: bool) -> None:
        bubble = _Bubble(text=text, is_user=is_user)
        self._history.add_widget(bubble)
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: setattr(self._scroll, "scroll_y", 0), 0.1)

    def _do_send(self) -> None:
        text = self._input.text.strip()
        if not text:
            return
        self._input.text = ""
        self._on_send(text)

    def _do_overwhelmed(self) -> None:
        self._on_overwhelmed()

    def _default_send(self, text: str) -> None:
        """Fallback when no on_send callback is wired."""
        self.add_user_message(text)
        self.add_assistant_message(
            "AI integration is not yet connected. "
            "Please check back in Milestone 2!"
        )

    def _default_overwhelmed(self) -> None:
        """Fallback when no on_overwhelmed callback is wired."""
        self.add_assistant_message(
            "I hear you! AI is not yet connected. "
            "Try starting with your highest-priority task for just 10 minutes."
        )
