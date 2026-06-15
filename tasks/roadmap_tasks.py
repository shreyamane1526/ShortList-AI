from __future__ import annotations

from typing import Any, Dict

import core.root  # noqa: F401
from core.celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def generate_roadmap_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Foundation Celery task for roadmap generation.

    IMPORTANT:
    - Does not change existing business logic yet.
    - Intentionally returns payload passthrough when roadmap code not yet wired.
    """
    # In Phase 3 foundation we avoid extracting real logic until explicit follow-up.
    return {"status": "not_implemented_yet", "payload": payload, "task_id": self.request.id}

