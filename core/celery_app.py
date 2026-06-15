from __future__ import annotations

import os

import core.root  # noqa: F401
from core.config import settings


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/0")
)


def make_celery_app():
    from celery import Celery

    app = Celery(
        "shortlist_ai",
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
    )

    # Keep defaults conservative; foundation only.
    app.conf.update(
        broker_connection_retry_on_startup=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_default_queue="default",
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )

    return app


celery_app = make_celery_app()

