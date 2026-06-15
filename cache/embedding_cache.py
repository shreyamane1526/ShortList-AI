from __future__ import annotations

import json
import logging
import hashlib
from typing import Any, Optional, List

import core.root  # noqa: F401
from core.config import settings

logger = logging.getLogger(__name__)


def _json_dumps_safe(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _json_loads_safe(raw: str) -> Any:
    return json.loads(raw)


def compute_embedding_key(
    kind: str,
    model_name: str,
    text: str,
    extra: Optional[dict[str, Any]] = None,
) -> str:
    """Deterministic cache key for embedding vectors.

    IMPORTANT: This must not change embedding behavior or similarity logic.
    It only memoizes vectors produced by the existing embedding model.
    """
    payload: dict[str, Any] = {
        "kind": kind,
        "model": model_name,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extra": extra or {},
    }
    raw = _json_dumps_safe(payload)
    return f"emb:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def _get_redis(redis_client: Any):
    return redis_client


def get_cached_embedding(redis_client: Any, key: str) -> Optional[List[float]]:
    """Return cached embedding (list[float]) or None."""
    r = _get_redis(redis_client)
    try:
        raw = r.get(key)
    except Exception:
        logger.exception("embedding_cache.get failed")
        return None

    if raw is None:
        logger.info("embedding_cache miss key=%s", key)
        return None

    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        data = _json_loads_safe(raw)
        emb = data.get("embedding")
        logger.info("embedding_cache hit key=%s", key)
        return emb
    except Exception:
        logger.exception("embedding_cache parse failed")
        return None


def set_cached_embedding(
    redis_client: Any,
    key: str,
    embedding: List[float],
    ttl_seconds: Optional[int] = None,
) -> None:
    """Store embedding in Redis as JSON."""
    r = _get_redis(redis_client)
    ttl_seconds = ttl_seconds if ttl_seconds is not None else int(settings.CACHE_TTL_HOURS * 3600)

    payload = {"embedding": embedding}
    raw = _json_dumps_safe(payload)

    try:
        r.set(name=key, value=raw, ex=ttl_seconds)
        logger.info("embedding_cache set key=%s ttl_seconds=%s", key, ttl_seconds)
    except Exception:
        logger.exception("embedding_cache.set failed")

