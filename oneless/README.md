# OneLess

AI-assisted personal task manager built with Python and Kivy.

👉 **New here? See the [Quick Start Guide](QUICKSTART.md) for step-by-step setup instructions.**

---

## Requirements

- **Python 3.10 – 3.13** (Python 3.14 is not yet supported by Kivy's Windows binaries)
- pip

> **Note for Python 3.14 users:** Kivy's Windows SDL2 dependency (`kivy_deps.sdl2_dev`) does not yet ship a wheel for Python 3.14. Until Kivy releases updated packages, please use Python 3.13 on Windows. The backend layers (models, persistence, services) are fully tested and work on Python 3.14. Only the Kivy UI layers require 3.10–3.13.

## Setup

> **Important:** all commands below must be run from inside the **`oneless`**
> subfolder (the one that contains `main.py`), not the repository root.
> If your terminal starts in the repo root, run `cd oneless` first.

```powershell
# 1. Create a virtual environment
py -3.13 -m venv venv

# 2. Activate it
# Windows (from inside the oneless folder)
venv\Scripts\activate
# Windows (from the repo root — Oneless Task Manager)
# .\oneless\venv\Scripts\activate  &&  cd oneless
# macOS / Linux
# source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Configure AI provider
#    Copy .env.example to .env and edit as needed.
#    The default mock provider works without any credentials.
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

## Running the application

```powershell
# Ensure the venv is active and your terminal is in the oneless folder, then:
python main.py
```

The SQLite database is created automatically at `data/oneless.db` on first run.

## Running the tests

The core tests (models, persistence, services) do not require Kivy:

```bash
python tests/test_core.py
```

Expected output:
```
Ran 18 tests in ~1s
OK
```

## Project structure

```
oneless/
├── main.py                        # Entry point
├── requirements.txt
├── .env.example                   # Credential template (copy to .env)
├── tests/
│   └── test_core.py               # Unit + integration tests (no Kivy needed)
└── oneless/
    ├── models/
    │   └── task.py                # Task and Subtask dataclasses
    ├── persistence/
    │   └── repository.py          # SQLite repository (all DB queries)
    ├── services/
    │   └── task_service.py        # Business logic, filtering, validation
    ├── ai/                        # AI provider interface (Milestone 2)
    └── ui/
        ├── app.py                 # Kivy App subclass
        ├── main_screen.py         # Three-column root layout
        ├── calendar_widget.py     # Month-view calendar
        ├── task_list_widget.py    # Task list + filter tabs
        ├── task_detail_widget.py  # Centre panel — view/edit task
        └── ai_sidebar_widget.py   # Right panel — chat sidebar (stub)
```

## Milestones

| # | Description | Status |
|---|---|---|
| 1 | Functional task manager (calendar, list, detail, CRUD, SQLite) | ✅ Done |
| 2 | AI chat sidebar, natural-language task operations via Gemini 2.5 Flash Lite | ✅ Done |
| 3 | Calendar-aware assistance, scheduling suggestions | 🔲 Planned |
| 4 | Polish, keyboard nav, optional voice input | 🔲 Planned |

## AI provider

Set `AI_PROVIDER` in `.env`:

| Value | Description |
|---|---|
| `mock` | Deterministic responses, no credentials needed (default) |
| `gemini` | Google Gemini 2.5 Flash Lite — requires `GEMINI_API_KEY` |

Get a free Gemini API key at **https://aistudio.google.com/apikey**

### What the AI can do (Milestone 2)

- **Create tasks** — "Add a task to submit the report by Friday at 5pm"
- **Update tasks** — "Change the priority of the groceries task to high"
- **Complete tasks** — "Mark the dentist appointment as done"
- **Delete tasks** — "Remove the old meeting task"
- **Answer questions** — "What tasks do I have due this week?"

## Architecture

The application is divided into clearly separated layers:

- **Models** (`oneless/models/`) — pure Python dataclasses, no I/O.
- **Persistence** (`oneless/persistence/`) — all SQLite access; no other layer issues SQL.
- **Services** (`oneless/services/`) — validation, business logic, filtering. No UI/DB imports.
- **AI** (`oneless/ai/`) — provider-agnostic interface; implemented in Milestone 2.
- **UI** (`oneless/ui/`) — Kivy widgets; calls services only; no direct DB access.

## Notes

- No API keys or secrets should ever be committed to the repository.
- The `data/` directory and `.env` file are both gitignored.
- All timestamps are stored as ISO-8601 UTC strings.
