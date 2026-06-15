from __future__ import annotations

from typing import Any, Dict

import core.root  # noqa: F401
from core.celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def retrain_models_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Foundation Celery task for retraining jobs."""
    return {"status": "not_implemented_yet", "payload": payload, "task_id": self.request.id}

