"""
Kivy App subclass — configures window and builds root widget.
"""
from __future__ import annotations

import os

from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window

from oneless.services.task_service import TaskService
from oneless.ui.main_screen import MainScreen

# Window defaults (before App.run())
Config.set("graphics", "width", "1280")
Config.set("graphics", "height", "800")
Config.set("graphics", "minimum_width", "800")
Config.set("graphics", "minimum_height", "600")
Config.set("input", "mouse", "mouse,multitouch_on_demand")


class OneLessApp(App):
    title = "OneLess"

    def build(self):
        Window.clearcolor = (0.13, 0.13, 0.15, 1)
        service = TaskService()
        return MainScreen(service=service)

    def on_stop(self):
        # Ensure the repository connection is closed cleanly
        if self.root and hasattr(self.root, "_service"):
            repo = getattr(self.root._service, "_repo", None)
            if repo:
                repo.close()
