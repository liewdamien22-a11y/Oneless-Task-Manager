"""
Music playback placeholder.

This module reserves a place in the codebase for a potential future
focus-music feature.  No audio libraries are imported or used.

DO NOT add real audio playback here.  See the TODO below.
"""
from __future__ import annotations

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

_SURFACE = (0.17, 0.17, 0.20, 1)
_MUTED   = (0.45, 0.45, 0.50, 1)


def play_focus_music_placeholder() -> None:
    """TODO: Implement optional focus music playback in a future update."""
    pass


class MusicPlaceholderWidget(BoxLayout):
    """
    A small, visibly disabled UI element that reserves space for a
    future focus-music feature.  Performs no audio operations.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", "28dp")
        kwargs.setdefault("spacing", 6)
        kwargs.setdefault("padding", [8, 4, 8, 4])
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*_SURFACE)
            rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda i, v: setattr(rect, "pos", v),
                  size=lambda i, v: setattr(rect, "size", v))

        lbl = Label(
            text="♪  Focus Music — Coming Soon",
            font_size="11sp",
            color=_MUTED,
            halign="left",
            valign="middle",
        )
        lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(lbl)

        # Widget is intentionally disabled — no interaction possible
        self.disabled = True
        self.opacity = 0.5
