"""
core/root.py

Adds the project root directory to sys.path so every module can do:
    from core.config import settings
    from agents.evidence_agent import ...

Works correctly on Windows, Linux, and macOS regardless of how Python
is invoked (python run.py, uvicorn api.main:app, pytest, etc).

Import this at the top of any file that needs cross-package imports:
    import core.root  # noqa: F401  (just the side-effect matters)
"""
import sys
import os

# Walk up from this file's location until we find the project root.
# The project root is the directory that contains pyproject.toml or run.py.
_here = os.path.dirname(os.path.abspath(__file__))        # .../shortlist_ai/core
_root = os.path.dirname(_here)                             # .../shortlist_ai

if _root not in sys.path:
    sys.path.insert(0, _root)