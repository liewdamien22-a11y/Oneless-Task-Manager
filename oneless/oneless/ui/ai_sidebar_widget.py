"""
AI assistant sidebar — right column.

Milestone 1: placeholder UI only (chat history, input field, Send button).
The actual AI integration is implemented in Milestone 2.
"""
from __future__ import annotations

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

_BG = (0.11, 0.11, 0.13, 1)
_SURFACE = (0.17, 0.17, 0.20, 1)
_ACCENT = (0.22, 0.44, 0.69, 1)
_TEXT = (0.92, 0.92, 0.94, 1)
_MUTED = (0.55, 0.55, 0.60, 1)
_USER_BUBBLE = (0.22, 0.44, 0.69, 0.85)
_AI_BUBBLE = (0.22, 0.22, 0.27, 1)


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
        bg_color = _USER_BUBBLE if is_user else _AI_BUBBLE
        _bg(self, bg_color)

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
        self.bind(
            minimum_height=self.setter("height"),
        )


class AISidebarWidget(BoxLayout):
    """
    Right-column AI chat sidebar.

    Milestone 1: stores messages locally and shows them in a scroll view.
    Milestone 2 will wire this to the AI service.
    """

    def __init__(self, on_send=None, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", 0)
        super().__init__(**kwargs)

        self._on_send = on_send or self._default_send
        _bg(self, _BG)

        self._build_header()
        self._build_history()
        self._build_input_bar()

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
    # Public
    # ------------------------------------------------------------------

    def add_user_message(self, text: str) -> None:
        self._add_message(text, is_user=True)

    def add_assistant_message(self, text: str) -> None:
        self._add_message(text, is_user=False)

    def set_loading(self, loading: bool) -> None:
        self._send_btn.disabled = loading
        self._send_btn.text = "…" if loading else "Send"

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
        header.add_widget(Label(
            text="AI Assistant",
            font_size="14sp", color=_TEXT, bold=True,
            halign="left", valign="middle",
        ))
        self.add_widget(header)

    def _build_history(self) -> None:
        self._scroll = ScrollView(size_hint=(1, 1))
        self._history = GridLayout(
            cols=1, size_hint_y=None, spacing=4, padding=[6, 6, 6, 6],
        )
        self._history.bind(minimum_height=self._history.setter("height"))
        self._scroll.add_widget(self._history)
        self.add_widget(self._scroll)

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

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_message(self, text: str, is_user: bool) -> None:
        bubble = _Bubble(text=text, is_user=is_user)
        self._history.add_widget(bubble)
        # Scroll to bottom after layout
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: setattr(self._scroll, "scroll_y", 0), 0.1)

    def _do_send(self) -> None:
        text = self._input.text.strip()
        if not text:
            return
        self._input.text = ""
        self._on_send(text)

    def _default_send(self, text: str) -> None:
        """Default handler used when no on_send callback is provided."""
        self.add_user_message(text)
        self.add_assistant_message(
            "AI integration is not yet connected. "
            "Please check back in Milestone 2!"
        )
