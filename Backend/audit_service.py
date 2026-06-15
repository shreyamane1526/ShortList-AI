"""Persist audit events to the audit_logs table for the admin dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from extensions import db
from models import AuditLog


def record_audit_log(
    action: str,
    entity_type: str,
    user_id: int | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
    created_at: datetime | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        ip_address=ip_address,
        details=details or {},
        created_at=created_at or datetime.utcnow(),
    )
    db.session.add(log)
    return log


def request_ip() -> str | None:
    from flask import request

    return request.headers.get("X-Forwarded-For", request.remote_addr)
