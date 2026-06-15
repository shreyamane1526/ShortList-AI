from __future__ import annotations

import threading
from typing import Any

import core.root  # noqa: F401


_lock = threading.Lock()
_client: Any = None


def get_http_client() -> Any:
    """Singleton httpx client (lazy)."""
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        import httpx

        _client = httpx.Client(timeout=20.0)
        return _client

