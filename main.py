"""
main.py — Project entry point

Delegates to the FastAPI application in api/main.py.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Or use the convenience script:
    python run.py          # CLI evaluation (no server needed)
"""
# Ensure project root is on sys.path regardless of how this is invoked
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.main import app  # noqa: F401 — re-exported for uvicorn

__all__ = ["app"]
