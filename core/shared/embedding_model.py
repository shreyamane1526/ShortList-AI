from __future__ import annotations

import threading
from typing import Any

import core.root  # noqa: F401
from core.config import settings


_model_lock = threading.Lock()
_model: Any = None


def get_embedding_model() -> Any:
    """Thread-safe singleton SentenceTransformer loader.

    IMPORTANT: This does not change embedding behavior; it only ensures the
    model is loaded once per process.
    """
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return _model

