"""
Task detail widget — centre panel.

Shows task details in view mode and switches to an edit form when the
user presses Edit.  Handles subtask management inline.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from oneless.models.task import Subtask, Task

# Palette
_BG = (0.13, 0.13, 0.15, 1)
_SURFACE = (0.18, 0.18, 0.21, 1)
_CARD = (0.20, 0.20, 0.24, 1)
_TEXT = (0.92, 0.92, 0.94, 1)
_MUTED = (0.55, 0.55, 0.60, 1)
_ACCENT = (0.22, 0.44, 0.69, 1)
_DANGER = (0.75, 0.22, 0.22, 1)
_SUCCESS = (0.22, 0.65, 0.38, 1)
_HIGH = (0.88, 0.42, 0.20, 1)
_MEDIUM = (0.88, 0.78, 0.20, 1)
_LOW = (0.35, 0.75, 0.45, 1)

_PRIORITY_COLORS = {"high": _HIGH, "medium": _MEDIUM, "low": _LOW}


def _bg(widget, color):
    with widget.canvas.before:
        Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda i, v: setattr(rect, "pos", v),
                size=lambda i, v: setattr(rect, "size", v))


def _lbl(text, font_size="13sp", color=_TEXT, bold=False,
         halign="left", markup=False, height="28dp") -> Label:
    l = Label(
        text=text, font_size=font_size, color=color,
        bold=bold, halign=halign, valign="middle",
        markup=markup,
        size_hint_y=None, height=height,
    )
    l.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
    return l


def _input(hint="", text="", multiline=False, height="34dp") -> TextInput:
    return TextInput(
        hint_text=hint, text=text,
        multiline=multiline,
        font_size="13sp",
        background_color=_CARD,
        foreground_color=_TEXT,
        cursor_color=_TEXT,
        hint_text_color=list(_MUTED),
        size_hint_y=None,
        height=height,
        padding=[8, 6, 8, 6],
    )


def _btn(text, color=_ACCENT, font_size="13sp", height="36dp") -> Button:
    b = Button(
        text=text, font_size=font_size,
        background_normal="", background_color=color,
        color=(1, 1, 1, 1),
        size_hint_y=None, height=height,
        bold=False,
    )
    return b


class TaskDetailWidget(BoxLayout):
    """
    Centre panel showing task details.

    Callbacks:
        on_save(task_id, fields)         — user pressed Save in edit mode
        on_delete(task_id)               — user confirmed deletion
        on_complete(task_id)             — mark task complete
        on_reopen(task_id)               — reopen completed task
        on_add_subtask(task_id, title)   — add a subtask
        on_complete_subtask(subtask_id)  — complete a subtask
        on_delete_subtask(subtask_id)    — delete a subtask
        on_create_new()                  — user wants to create a new task
    """

    def __init__(
        self,
        on_save: Callable = None,
        on_delete: Callable = None,
        on_complete: Callable = None,
        on_reopen: Callable = None,
        on_add_subtask: Callable = None,
        on_complete_subtask: Callable = None,
        on_delete_subtask: Callable = None,
        on_create_new: Callable = None,
        **kwargs,
    ):
        kwargs.setdefault("orientation", "vertical")
        super().__init__(**kwargs)

        self._on_save = on_save or (lambda *a, **k: None)
        self._on_delete = on_delete or (lambda *a: None)
        self._on_complete = on_complete or (lambda *a: None)
        self._on_reopen = on_reopen or (lambda *a: None)
        self._on_add_subtask = on_add_subtask or (lambda *a: None)
        self._on_complete_subtask = on_complete_subtask or (lambda *a: None)
        self._on_delete_subtask = on_delete_subtask or (lambda *a: None)
        self._on_create_new = on_create_new or (lambda: None)

        self._task: Optional[Task] = None
        self._edit_mode = False

        _bg(self, _BG)
        self._show_empty_state()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def show_task(self, task: Task) -> None:
        self._task = task
        self._edit_mode = False
        self._rebuild()

    def show_empty(self) -> None:
        self._task = None
        self._edit_mode = False
        self._show_empty_state()

    def enter_edit_mode(self) -> None:
        if self._task:
            self._edit_mode = True
            self._rebuild()

    def enter_create_mode(self) -> None:
        """Show a blank edit form for a brand-new task."""
        self._task = None
        self._edit_mode = True
        self._rebuild()

    # ------------------------------------------------------------------
    # Empty state
    # ------------------------------------------------------------------

    def _show_empty_state(self) -> None:
        self.clear_widgets()
        box = BoxLayout(orientation="vertical", spacing=12, padding=32)
        box.add_widget(Label(
            text="No task selected",
            font_size="16sp", color=_MUTED, bold=True,
        ))
        box.add_widget(Label(
            text="Select a task from the list or create a new one.",
            font_size="13sp", color=_MUTED,
        ))
        btn = _btn("+ Create New Task", color=_ACCENT, height="40dp")
        btn.bind(on_press=lambda *_: self._on_create_new())
        btn.size_hint_x = 0.4
        btn.pos_hint = {"center_x": 0.5}
        box.add_widget(btn)
        self.add_widget(box)

    # ------------------------------------------------------------------
    # Rebuild
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        self.clear_widgets()
        if self._edit_mode:
            self._build_edit_form()
        else:
            self._build_view()

    # ------------------------------------------------------------------
    # View mode
    # ------------------------------------------------------------------

    def _build_view(self) -> None:
        task = self._task
        scroll = ScrollView()
        container = GridLayout(cols=1, size_hint_y=None, spacing=6, padding=[16, 16, 16, 16])
        container.bind(minimum_height=container.setter("height"))

        # Title
        container.add_widget(_lbl(
            task.title, font_size="18sp", bold=True, height="40dp",
            color=_TEXT,
        ))

        # Status / priority chips
        chips = BoxLayout(orientation="horizontal", size_hint_y=None, height="28dp", spacing=8)
        status_text = "✓ Completed" if task.completed else "● Open"
        status_color = _SUCCESS if task.completed else _MUTED
        chips.add_widget(_lbl(status_text, color=status_color, font_size="12sp", height="28dp"))
        prio_color = _PRIORITY_COLORS.get(task.priority, _MUTED)
        chips.add_widget(_lbl(
            f"[{task.priority.capitalize()}]", color=prio_color,
            font_size="12sp", height="28dp",
        ))
        container.add_widget(chips)

        # Due date
        if task.due_date:
            due_str = task.due_date + (" " + task.due_time if task.due_time else "")
            container.add_widget(_lbl(f"Due: {due_str}", color=_MUTED, font_size="12sp"))

        # Category
        if task.category:
            container.add_widget(_lbl(f"Category: {task.category}", color=_MUTED, font_size="12sp"))

        # Duration
        if task.estimated_duration:
            container.add_widget(_lbl(
                f"Estimated: {task.estimated_duration} min",
                color=_MUTED, font_size="12sp",
            ))

        # Description
        if task.description:
            container.add_widget(_lbl("Description", font_size="12sp", color=_MUTED))
            desc = Label(
                text=task.description,
                font_size="13sp", color=_TEXT,
                halign="left", valign="top",
                size_hint_y=None,
            )
            desc.bind(
                size=lambda i, v: (setattr(i, "text_size", (v[0], None))),
                texture_size=lambda i, v: setattr(i, "height", v[1] + 8),
            )
            container.add_widget(desc)

        # Subtasks
        container.add_widget(_lbl("Subtasks", font_size="13sp", bold=True, height="32dp"))
        if task.subtasks:
            for st in sorted(task.subtasks, key=lambda s: (s.position, s.created_at)):
                self._build_subtask_row(container, st)
        else:
            container.add_widget(_lbl("No subtasks.", color=_MUTED, font_size="12sp"))

        # Add subtask
        add_row = BoxLayout(orientation="horizontal", size_hint_y=None, height="34dp", spacing=6)
        self._new_subtask_input = _input(hint="New subtask title…", height="34dp")
        add_btn = _btn("Add", height="34dp", color=_ACCENT)
        add_btn.size_hint_x = None
        add_btn.width = "60dp"
        add_btn.bind(on_press=lambda *_: self._submit_subtask())
        add_row.add_widget(self._new_subtask_input)
        add_row.add_widget(add_btn)
        container.add_widget(add_row)

        # Timestamps
        container.add_widget(_lbl(
            f"Created: {task.created_at[:19].replace('T', ' ')}",
            color=_MUTED, font_size="11sp",
        ))
        container.add_widget(_lbl(
            f"Updated: {task.updated_at[:19].replace('T', ' ')}",
            color=_MUTED, font_size="11sp",
        ))

        scroll.add_widget(container)
        self.add_widget(scroll)

        # Action buttons
        self._build_action_bar()

    def _build_subtask_row(self, container: GridLayout, st: Subtask) -> None:
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height="32dp", spacing=4)
        check_text = "☑" if st.completed else "☐"
        check_btn = Button(
            text=check_text,
            font_size="16sp",
            size_hint_x=None, width="32dp",
            background_normal="", background_color=(0, 0, 0, 0),
            color=_SUCCESS if st.completed else _TEXT,
        )
        check_btn.bind(on_press=lambda *_, sid=st.id: self._on_complete_subtask(sid))

        title_color = _MUTED if st.completed else _TEXT
        title_lbl = _lbl(
            ("[s]" + st.title + "[/s]") if st.completed else st.title,
            color=title_color, font_size="13sp", markup=True, height="32dp",
        )

        del_btn = Button(
            text="✕",
            font_size="12sp",
            size_hint_x=None, width="28dp",
            background_normal="", background_color=(0, 0, 0, 0),
            color=_DANGER,
        )
        del_btn.bind(on_press=lambda *_, sid=st.id: self._confirm_delete_subtask(sid))

        row.add_widget(check_btn)
        row.add_widget(title_lbl)
        row.add_widget(del_btn)
        container.add_widget(row)

    def _build_action_bar(self) -> None:
        bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="44dp",
            spacing=6, padding=[12, 4, 12, 4],
        )
        _bg(bar, _SURFACE)

        edit_btn = _btn("Edit", color=_ACCENT, height="36dp")
        edit_btn.bind(on_press=lambda *_: self.enter_edit_mode())
        bar.add_widget(edit_btn)

        if self._task.completed:
            reopen_btn = _btn("Reopen", color=_SUCCESS, height="36dp")
            reopen_btn.bind(on_press=lambda *_: self._on_reopen(self._task.id))
            bar.add_widget(reopen_btn)
        else:
            done_btn = _btn("Mark Complete", color=_SUCCESS, height="36dp")
            done_btn.bind(on_press=lambda *_: self._on_complete(self._task.id))
            bar.add_widget(done_btn)

        del_btn = _btn("Delete", color=_DANGER, height="36dp")
        del_btn.bind(on_press=lambda *_: self._confirm_delete_task())
        bar.add_widget(del_btn)

        self.add_widget(bar)

    # ------------------------------------------------------------------
    # Edit / create form
    # ------------------------------------------------------------------

    def _build_edit_form(self) -> None:
        task = self._task  # May be None for new task

        scroll = ScrollView()
        container = GridLayout(cols=1, size_hint_y=None, spacing=8,
                               padding=[16, 16, 16, 16])
        container.bind(minimum_height=container.setter("height"))

        heading = "Edit Task" if task else "New Task"
        container.add_widget(_lbl(heading, font_size="16sp", bold=True, height="36dp"))

        container.add_widget(_lbl("Title *", font_size="12sp", color=_MUTED))
        self._edit_title = _input(
            hint="Task title",
            text=task.title if task else "",
            height="36dp",
        )
        container.add_widget(self._edit_title)

        container.add_widget(_lbl("Description", font_size="12sp", color=_MUTED))
        self._edit_desc = _input(
            hint="Description (optional)",
            text=task.description if task else "",
            multiline=True,
            height="80dp",
        )
        container.add_widget(self._edit_desc)

        container.add_widget(_lbl("Due Date (YYYY-MM-DD)", font_size="12sp", color=_MUTED))
        self._edit_due_date = _input(
            hint="e.g. 2025-06-30",
            text=task.due_date if (task and task.due_date) else "",
            height="36dp",
        )
        container.add_widget(self._edit_due_date)

        container.add_widget(_lbl("Due Time (HH:MM)", font_size="12sp", color=_MUTED))
        self._edit_due_time = _input(
            hint="e.g. 14:30 (optional)",
            text=task.due_time if (task and task.due_time) else "",
            height="36dp",
        )
        container.add_widget(self._edit_due_time)

        container.add_widget(_lbl("Priority", font_size="12sp", color=_MUTED))
        prio_row = BoxLayout(orientation="horizontal", size_hint_y=None, height="36dp", spacing=4)
        self._prio_buttons: dict = {}
        current_prio = task.priority if task else "medium"
        for p in ("low", "medium", "high"):
            active = (p == current_prio)
            pb = Button(
                text=p.capitalize(),
                font_size="12sp",
                background_normal="",
                background_color=_PRIORITY_COLORS[p] if active else _SURFACE,
                color=(1, 1, 1, 1),
            )
            pb.bind(on_press=lambda b, pv=p: self._select_priority(pv))
            prio_row.add_widget(pb)
            self._prio_buttons[p] = pb
        self._selected_priority = current_prio
        container.add_widget(prio_row)

        container.add_widget(_lbl("Category", font_size="12sp", color=_MUTED))
        self._edit_category = _input(
            hint="e.g. Study, Work, Personal",
            text=task.category if task else "",
            height="36dp",
        )
        container.add_widget(self._edit_category)

        container.add_widget(_lbl("Estimated Duration (minutes)", font_size="12sp", color=_MUTED))
        self._edit_duration = _input(
            hint="e.g. 90",
            text=str(task.estimated_duration) if (task and task.estimated_duration) else "",
            height="36dp",
        )
        container.add_widget(self._edit_duration)

        scroll.add_widget(container)
        self.add_widget(scroll)

        # Save / Cancel bar
        bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="44dp",
            spacing=6, padding=[12, 4, 12, 4],
        )
        _bg(bar, _SURFACE)

        save_btn = _btn("Save", color=_ACCENT, height="36dp")
        save_btn.bind(on_press=lambda *_: self._submit_edit())
        bar.add_widget(save_btn)

        cancel_btn = _btn("Cancel", color=_MUTED, height="36dp")
        cancel_btn.bind(on_press=lambda *_: self._cancel_edit())
        bar.add_widget(cancel_btn)

        self.add_widget(bar)

    def _select_priority(self, priority: str) -> None:
        self._selected_priority = priority
        for p, btn in self._prio_buttons.items():
            btn.background_color = _PRIORITY_COLORS[p] if p == priority else _SURFACE

    def _submit_edit(self) -> None:
        fields = {
            "title": self._edit_title.text.strip(),
            "description": self._edit_desc.text.strip(),
            "due_date": self._edit_due_date.text.strip() or None,
            "due_time": self._edit_due_time.text.strip() or None,
            "priority": self._selected_priority,
            "category": self._edit_category.text.strip(),
            "estimated_duration": self._parse_duration(),
        }
        task_id = self._task.id if self._task else None
        self._on_save(task_id, fields)

    def _parse_duration(self) -> Optional[int]:
        raw = self._edit_duration.text.strip()
        try:
            v = int(raw)
            return v if v > 0 else None
        except (ValueError, TypeError):
            return None

    def _cancel_edit(self) -> None:
        if self._task:
            self._edit_mode = False
            self._rebuild()
        else:
            self._show_empty_state()

    # ------------------------------------------------------------------
    # Subtask actions
    # ------------------------------------------------------------------

    def _submit_subtask(self) -> None:
        title = self._new_subtask_input.text.strip()
        if title and self._task:
            self._on_add_subtask(self._task.id, title)

    # ------------------------------------------------------------------
    # Confirmations
    # ------------------------------------------------------------------

    def _confirm_delete_task(self) -> None:
        content = BoxLayout(orientation="vertical", spacing=12, padding=12)
        content.add_widget(Label(
            text=f"Delete '{self._task.title}'?\nThis cannot be undone.",
            font_size="14sp", color=_TEXT, halign="center",
        ))
        btns = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height="40dp")
        popup = Popup(
            title="Confirm Delete", content=content,
            size_hint=(0.5, 0.3), auto_dismiss=False,
        )
        ok = _btn("Delete", color=_DANGER)
        ok.bind(on_press=lambda *_: (popup.dismiss(), self._on_delete(self._task.id)))
        cancel = _btn("Cancel", color=_MUTED)
        cancel.bind(on_press=lambda *_: popup.dismiss())
        btns.add_widget(ok)
        btns.add_widget(cancel)
        content.add_widget(btns)
        popup.open()

    def _confirm_delete_subtask(self, subtask_id: str) -> None:
        content = BoxLayout(orientation="vertical", spacing=12, padding=12)
        content.add_widget(Label(
            text="Delete this subtask?",
            font_size="14sp", color=_TEXT, halign="center",
        ))
        btns = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height="40dp")
        popup = Popup(
            title="Confirm", content=content,
            size_hint=(0.45, 0.25), auto_dismiss=False,
        )
        ok = _btn("Delete", color=_DANGER)
        ok.bind(on_press=lambda *_: (popup.dismiss(), self._on_delete_subtask(subtask_id)))
        cancel = _btn("Cancel", color=_MUTED)
        cancel.bind(on_press=lambda *_: popup.dismiss())
        btns.add_widget(ok)
        btns.add_widget(cancel)
        content.add_widget(btns)
        popup.open()
