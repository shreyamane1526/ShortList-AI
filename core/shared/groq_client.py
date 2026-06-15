from __future__ import annotations

import threading
from typing import Any

import core.root  # noqa: F401
from core.config import settings


_lock = threading.Lock()
_client: Any = None


def get_groq_client() -> Any:
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        from groq import Groq

        _client = Groq(api_key=settings.GROQ_API_KEY)
        return _client

