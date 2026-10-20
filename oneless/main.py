"""
OneLess — entry point.

Usage:
    python main.py
"""
import os
import sys

# Ensure the workspace root is on sys.path so `oneless` package is importable
# when the script is run from the project root.
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from oneless.ui.app import OneLessApp

if __name__ == "__main__":
    OneLessApp().run()
