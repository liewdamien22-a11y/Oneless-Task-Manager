# OneLess — Quick Start Guide

Everything you need to go from zero to a running app.

---

## Before you begin

You do **not** need Git, an internet connection after setup, or any accounts.
All data is stored locally on your machine.

---

## Step 1 — Install Python 3.13

Kivy's Windows packages currently support **Python 3.10 – 3.13 only**.
Python 3.14 will not work until Kivy releases updated binaries for it.

1. Go to **https://www.python.org/downloads/release/python-3130/**
2. Scroll to the **Files** section and download **Windows installer (64-bit)**
3. Run the installer
   - ✅ **Check "Add Python to PATH"** on the first screen before clicking Install
4. Confirm the install worked — open a new terminal and run:
   ```powershell
   py --list
   ```
   You should see `-3.13` in the list.

> If you already have other Python versions installed, that's fine — they won't interfere.

---

## Step 2 — Open the project in VS Code

1. Open VS Code
2. Open the **`oneless`** subfolder (not the repository root):
   - Menu → **File → Open Folder…** and select the `oneless` folder inside the repo
3. Open the terminal inside VS Code:
   - Menu → **Terminal → New Terminal**, or press **Ctrl + `** (backtick)
4. Confirm your terminal is in the right place:
   ```powershell
   Get-Location
   ```
   It should show a path ending in `oneless` (e.g. `…\Oneless Task Manager\oneless`).

> **Already opened the repo root by mistake?**
> That's fine — just `cd oneless` in the terminal before continuing, or use the
> full paths shown in the note below Step 4.

---

## Step 3 — Create a virtual environment

A virtual environment keeps OneLess's dependencies separate from everything
else on your machine.

```powershell
py -3.13 -m venv venv
```

A `venv/` folder will appear in the project directory.

---

## Step 4 — Activate the virtual environment

```powershell
venv\Scripts\activate
```

**How to tell it worked:** your terminal prompt changes to show `(venv)` at the start:

```
(venv) PS C:\...\Oneless Task Manager\oneless>
```

If you ever open a new terminal window, you'll need to run this activate
command again before running the app.

> **If your terminal is in the repo root** (`Oneless Task Manager`) instead of
> the `oneless` subfolder, use the longer path:
> ```powershell
> .\oneless\venv\Scripts\activate
> cd oneless
> ```

---

## Step 5 — Install dependencies

```powershell
pip install -r requirements.txt
```

This downloads Kivy and its graphics libraries. It takes **1–3 minutes**
depending on your connection. Wait for the line:

```
Successfully installed kivy-2.3.x ...
```

> If you see an error mentioning `kivy_deps.sdl2_dev`, your Python version
> is not 3.13. Go back to Step 1.

---

## Step 6 — Run the application

```powershell
python main.py
```

A window will open with the three-column OneLess interface:

- **Left column** — month calendar + task list with filters
- **Centre column** — task details and edit form
- **Right column** — AI assistant chat sidebar

The database file (`data/oneless.db`) is created automatically on first launch.
Your tasks persist across restarts.

---

## Step 7 — (Optional) Configure the AI provider

The app works out of the box with a built-in **mock AI** — no credentials needed.
Only do this step if you want to connect a real AI model.

1. Copy the example config:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` in any text editor and set your provider:

   | Setting | What to put there |
   |---|---|
   | `AI_PROVIDER=mock` | Leave as-is to use the built-in mock (default) |
   | `AI_PROVIDER=openai` | Change to this if you have an OpenAI API key |
   | `OPENAI_API_KEY=` | Paste your OpenAI key here |
   | `WATSONX_*` | Fill in only if using IBM watsonx |

   > ⚠️ Never share your `.env` file. It is gitignored and will never be
   > committed to version control.

---

## Every time you come back

You only need Steps 3–4 once. After that, each session is just:

```powershell
# 1. Activate the environment (if not already active)
venv\Scripts\activate

# 2. Run the app
python main.py
```

> **If your terminal starts in the repo root** (`Oneless Task Manager`):
> ```powershell
> .\oneless\venv\Scripts\activate
> cd oneless
> python main.py
> ```

---

## Running the tests

The core logic tests run without Kivy and verify models, database, and
business logic:

```powershell
python tests/test_core.py
```

Expected output:
```
Ran 18 tests in ~1s
OK
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `py --list` doesn't show 3.13 | Reinstall Python 3.13 with "Add to PATH" checked |
| `python` opens the Microsoft Store | Reinstall Python 3.13 with "Add to PATH" checked |
| `kivy_deps.sdl2_dev` error during install | You're using Python 3.14 — go back to Step 1 |
| `ModuleNotFoundError: No module named 'kivy'` | Virtual environment isn't active — run `venv\Scripts\activate` (or `.\oneless\venv\Scripts\activate` from the repo root) |
| `(venv)` disappeared from prompt | Open a new terminal and run `venv\Scripts\activate` again |
| `venv\Scripts\activate` says "module could not be loaded" | Your terminal is in the repo root, not the `oneless` folder — run `.\oneless\venv\Scripts\activate` then `cd oneless` |
| App window is black or crashes immediately | Update your graphics drivers; Kivy requires OpenGL 2.0+ |
| Tasks not saving between restarts | Check that the `data/` folder exists and you have write access to the project folder |
| VS Code asks "select interpreter for workspace" | Click **Yes** and choose the `venv` Python — this is the right one |
