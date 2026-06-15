from __future__ import annotations

import threading
from typing import Any

import core.root  # noqa: F401
from core.config import settings


_redis_lock = threading.Lock()
_redis: Any = None


def get_redis_client() -> Any:
    """Singleton Redis client.

    Uses REDIS_URL from env if available; otherwise defaults to redis:6379.
    """
    global _redis
    if _redis is not None:
        return _redis

    with _redis_lock:
        if _redis is not None:
            return _redis

        import os
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

        import redis

        _redis = redis.Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=3,
            socket_timeout=5,
            health_check_interval=30,
        )
        # Do not block forever; just ping.
        _redis.ping()
        return _redis

