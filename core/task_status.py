from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import core.root  # noqa: F401
from core.shared.redis_client import get_redis_client


@dataclass(frozen=True)
class TaskState:
    status: str
    progress: int = 0
    error: Optional[str] = None
    updated_at: float = time.time()


def _task_key(task_id: str) -> str:
    return f"task:{task_id}"



def set_task_state(task_id: str, state: TaskState, ttl_seconds: int = 7 * 24 * 3600) -> None:
    r = get_redis_client()
    payload = {
        "status": state.status,
        "progress": state.progress,
        "error": state.error,
        "updated_at": state.updated_at,
    }
    r.set(_task_key(task_id), json.dumps(payload, ensure_ascii=False), ex=ttl_seconds)


def get_task_state(task_id: str) -> Dict[str, Any]:
    r = get_redis_client()
    raw = r.get(_task_key(task_id))
    if raw is None:
        return {"status": "unknown", "progress": 0}
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def mark_queued(task_id: str) -> None:
    set_task_state(task_id, TaskState(status="queued", progress=0))


def mark_processing(task_id: str, progress: int = 25) -> None:
    set_task_state(task_id, TaskState(status="processing", progress=progress))


def mark_completed(task_id: str, progress: int = 100) -> None:
    set_task_state(task_id, TaskState(status="completed", progress=progress))


def mark_failed(task_id: str, error: str, progress: int = 0) -> None:
    set_task_state(task_id, TaskState(status="failed", progress=progress, error=error))

