from __future__ import annotations
from datetime import datetime, timedelta, timezone
from flask import Blueprint, current_app, jsonify, request, Response
from auth import current_user, login_required
from extensions import db
from models import (
    AlertSubscription, Application, AuditLog, BiasAlert, Candidate,
    CandidateInterview, CandidateJobEvaluation, FeedbackReport, Job,
    JobAlert, Message, Notification, Recruiter, Region, ScrapedJob, User,
)
from serializers import (
    admin_user_to_dict, application_to_dict, audit_log_to_dict,
    bias_alert_to_dict, candidate_to_dict, evaluation_to_dict, job_to_dict,
    message_to_dict, notification_to_dict, recruiter_to_dict, region_to_dict,
    scraped_job_to_dict, public_nd_inclusion,
)
from audit_service import record_audit_log, request_ip

_record_audit_log = record_audit_log  # keep existing admin handlers unchanged

import os
import requests as http_requests
from werkzeug.utils import secure_filename

api_bp = Blueprint("api", __name__)

def _push_notification(user_id, type_, title, body="", link=""):
    notif = Notification(user_id=user_id, type=type_, title=title, body=body, link=link)
    db.session.add(notif)

def _require_role(user, *roles):
    if user.role not in roles:
        return jsonify({"error": "Forbidden"}), 403
    return None

def _normalize_nd_type(value):
    if not value:
        return None
    nd_type = str(value).strip().lower()
    allowed = {"adhd", "dyslexia", "autism", "other"}
    return nd_type if nd_type in allowed else "other"

def _apply_candidate_profile_data(profile, data):
    for f in ("headline","location","summary","years_experience","skills","links","preferred_region_id"):
        if f in data: setattr(profile, f, data[f])
    if "projects" in data: profile.projects = data["projects"]
    if "neurodivergent" in data:
        value = data.get("neurodivergent")
        profile.neurodivergent = value if value in (True, False, None) else None
        profile.nd_type = _normalize_nd_type(data.get("nd_type")) if profile.neurodivergent is True else None
    elif "nd_type" in data and profile.neurodivergent is True:
        profile.nd_type = _normalize_nd_type(data.get("nd_type"))


def _build_cultural_dna_evidence(candidate: Candidate) -> dict:
    """Build real evidence payload from persisted candidate data for DNA backfill."""
    return {
        "headline": candidate.headline or "",
        "summary": candidate.summary or "",
        "skills": list(candidate.skills or []) + list(candidate.resume_skills or []),
        "projects": candidate.projects or [],
        "resume_projects": getattr(candidate, "resume_projects", None) or [],
        "github_repos_data": getattr(candidate, "github_repos_data", None) or [],
    }


def _ensure_cultural_dna(ev: CandidateJobEvaluation) -> bool:
    """
    Backfill cultural DNA for older evaluations that predate this field.
    Returns True when the evaluation was modified.
    """
    current = ev.cultural_dna or {}
    if isinstance(current, dict) and isinstance(current.get("dimensions"), list) and current["dimensions"]:
        return False

    if not ev.candidate or not ev.job:
        return False

    try:
        try:
            from agents.context_agent.cultural_extractor import extract_cultural_dna
        except ModuleNotFoundError:
            current_app.logger.warning(
                "agents.context_agent not found via normal import "
                "(Backend/agents/ shadows root agents/) — loading via direct path"
            )
            from agents import _import_root_agents_module
            _mod = _import_root_agents_module("context_agent.cultural_extractor")
            extract_cultural_dna = _mod.extract_cultural_dna
        except Exception as import_err:
            current_app.logger.warning(
                "Unexpected error importing cultural_extractor: %s — trying direct path",
                import_err,
            )
            from agents import _import_root_agents_module
            _mod = _import_root_agents_module("context_agent.cultural_extractor")
            extract_cultural_dna = _mod.extract_cultural_dna

        evidence = _build_cultural_dna_evidence(ev.candidate)
        cultural_dna = extract_cultural_dna(
            job_description=((ev.job.description or "") + " " + " ".join(ev.job.skills_required or [])).strip(),
            evidence=evidence,
            company_name=ev.job.company or "Company",
        )
        cultural_dna["candidate_name"] = ev.candidate.user.full_name if ev.candidate and ev.candidate.user else ""
        ev.cultural_dna = cultural_dna
        return True
    except Exception as exc:
        current_app.logger.warning("Cultural DNA backfill failed for evaluation %s: %s", ev.id, exc)
        return False

def _ensure_application_and_evaluation_for_pair(job: Job, candidate: Candidate) -> tuple[Application, CandidateJobEvaluation, bool]:
    app_ = Application.query.filter_by(job_id=job.id, candidate_id=candidate.id).first()
    ev = CandidateJobEvaluation.query.filter_by(job_id=job.id, candidate_id=candidate.id).first()
    created = False
    if not app_:
        app_ = Application(job_id=job.id, candidate_id=candidate.id, status="applied")
        db.session.add(app_)
        created = True
    if not ev:
        ev = CandidateJobEvaluation(
            job_id=job.id,
            candidate_id=candidate.id,
            eval_status="pending",
            recommendation="PENDING",
            recruiter_action="pending",
        )
        db.session.add(ev)
        created = True
    return app_, ev, created


def _auto_link_job_candidates(job: Job) -> dict:
    """
    Atomic self-healing linker: every candidate-job pair gets both application + evaluation.
    """
    candidates = Candidate.query.all()
    created_apps = 0
    created_evals = 0
    existing_pairs = 0
    created_eval_ids: list[int] = []
    for c in candidates:
        app_ = Application.query.filter_by(job_id=job.id, candidate_id=c.id).first()
        ev = CandidateJobEvaluation.query.filter_by(job_id=job.id, candidate_id=c.id).first()
        if app_ and ev:
            existing_pairs += 1
            continue
        if not app_:
            db.session.add(Application(job_id=job.id, candidate_id=c.id, status="applied"))
            created_apps += 1
        if not ev:
            ev = CandidateJobEvaluation(
                job_id=job.id,
                candidate_id=c.id,
                eval_status="pending",
                recommendation="PENDING",
                recruiter_action="pending",
            )
            db.session.add(ev)
            db.session.flush()
            created_evals += 1
            created_eval_ids.append(ev.id)
    return {
        "created_apps": created_apps,
        "created_evals": created_evals,
        "existing_pairs": existing_pairs,
        "created_eval_ids": created_eval_ids,
        "total_candidates": len(candidates),
    }

DEFAULT_AGENTS = [
    {"id": "evidence",  "name": "Evidence",  "desc": "Pulls real proof from GitHub, projects, portfolios", "status": "Active"},
    {"id": "context",   "name": "Context",   "desc": "Parses job requirements into weighted skills",        "status": "Active"},
    {"id": "reasoning", "name": "Reasoning", "desc": "Explains why each candidate matches",                 "status": "Active"},
    {"id": "ranking",   "name": "Ranking",   "desc": "Confidence-scored, side-by-side comparison",          "status": "Active"},
    {"id": "feedback",  "name": "Feedback",  "desc": "Personalized growth insights for every candidate",    "status": "Active"},
]


def _admin_only(user):
    return _require_role(user, "superadmin")


def _security_event_query():
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    return AuditLog.query.filter(
        AuditLog.created_at >= seven_days_ago,
        db.or_(
            AuditLog.entity_type.ilike("%security%"),
            AuditLog.action.ilike("%login%"),
            AuditLog.action.ilike("%auth%"),
            AuditLog.action.ilike("%failed%"),
            AuditLog.action.ilike("%password%"),
            AuditLog.action.ilike("%ip%"),
        ),
    )


def _bias_risk_from_assessment(text: str | None) -> str:
    content = (text or "").upper()
    if "AUTOMATIC ASSESSMENT UNAVAILABLE" in content:
        return "low"
    if "BIAS RISK" in content and "HIGH" in content:
        return "high"
    if "BIAS RISK" in content and "MEDIUM" in content:
        return "medium"
    if "BIAS RISK" in content and "LOW" in content:
        return "low"
    return "medium" if content.strip() else "low"


def _bias_summary_from_assessment(text: str | None) -> str:
    content = (text or "").strip()
    if not content:
        return "No fairness summary was generated."
    lines = [line.strip(" -*#") for line in content.splitlines() if line.strip()]
    for line in lines:
        if "bias risk" not in line.lower() and "fairness assessment" not in line.lower():
            return line[:220]
    return lines[0][:220] if lines else "Fairness assessment generated."


def _assessment_is_fallback(text: str | None) -> bool:
    content = (text or "").strip().lower()
    return "automatic assessment unavailable" in content or "manual review recommended" in content


def _is_meaningful_nd_inclusion(payload) -> bool:
    if not isinstance(payload, dict) or not payload:
        return False
    return any([
        bool(payload.get("nd_flag")),
        bool(payload.get("risk_of_underestimation")),
        bool(payload.get("recommended_action")),
        bool(payload.get("strengths_detected")),
        bool(payload.get("underestimation_risks")),
        payload.get("penalty_reduction_weight") not in (None, 0, 0.0),
    ])


def _report_to_admin_dict(report: FeedbackReport) -> dict:
    ev = report.evaluation
    candidate_name = ev.candidate.user.full_name if ev and ev.candidate and ev.candidate.user else f"Candidate #{ev.candidate_id if ev else '?'}"
    job_title = ev.job.title if ev and ev.job else "Unknown role"
    company = ev.job.company if ev and ev.job else ""
    risk = _bias_risk_from_assessment(report.fairness_assessment)
    return {
        "id": report.id,
        "evaluation_id": report.evaluation_id,
        "candidate_name": candidate_name,
        "job_title": job_title,
        "company": company,
        "score": ev.score if ev else None,
        "recommendation": ev.recommendation if ev else None,
        "fairness_assessment": report.fairness_assessment or "",
        "recruiter_summary": report.recruiter_summary or "",
        "interview_questions": report.interview_questions or [],
        "risk_level": risk,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "generation_time_ms": report.generation_time_ms,
    }


def _sync_admin_artifacts():
    existing_logs = AuditLog.query.all()
    existing_log_keys = {
        (log.details or {}).get("source_key")
        for log in existing_logs
        if isinstance(log.details, dict) and (log.details or {}).get("source_key")
    }
    existing_eval_ids = {
        (log.details or {}).get("evaluation_id")
        for log in existing_logs
        if log.action == "evaluation_completed"
        and isinstance(log.details, dict)
        and (log.details or {}).get("evaluation_id") is not None
    }
    existing_alert_keys = {
        f"{alert.bias_type}|{alert.description}"
        for alert in BiasAlert.query.all()
    }

    changed = False

    for entry in User.query.all():
        register_key = f"user-register:{entry.id}"
        if register_key not in existing_log_keys:
            record_audit_log(
                action="user_registered",
                entity_type="user",
                user_id=entry.id,
                details={
                    "source_key": register_key,
                    "email": entry.email,
                    "role": entry.role,
                },
                created_at=entry.created_at,
            )
            existing_log_keys.add(register_key)
            changed = True

        if entry.last_login_at:
            login_key = f"user-login:{entry.id}:{entry.last_login_at.isoformat()}"
            if login_key not in existing_log_keys:
                record_audit_log(
                    action="login_success",
                    entity_type="security",
                    user_id=entry.id,
                    details={
                        "source_key": login_key,
                        "email": entry.email,
                        "role": entry.role,
                    },
                    created_at=entry.last_login_at,
                )
                existing_log_keys.add(login_key)
                changed = True

    # Backfill evaluation completion logs
    evaluations = CandidateJobEvaluation.query.filter_by(eval_status="done").order_by(
        CandidateJobEvaluation.evaluated_at.desc().nullslast(),
        CandidateJobEvaluation.id.desc(),
    ).all()
    for ev in evaluations:
        if ev.id in existing_eval_ids:
            continue
        evaluated_at = ev.evaluated_at or ev.updated_at or datetime.utcnow()
        eval_key = f"evaluation-completed:{ev.id}:{evaluated_at.isoformat()}"
        record_audit_log(
            action="evaluation_completed",
            entity_type="evaluation",
            user_id=ev.candidate.user_id if ev.candidate and ev.candidate.user else None,
            details={
                "source_key": eval_key,
                "evaluation_id": ev.id,
                "candidate_id": ev.candidate_id,
                "job_id": ev.job_id,
                "candidate_name": ev.candidate.user.full_name if ev.candidate and ev.candidate.user else None,
                "job_title": ev.job.title if ev.job else None,
                "score": ev.score,
                "recommendation": ev.recommendation,
            },
            created_at=evaluated_at,
        )
        existing_log_keys.add(eval_key)
        existing_eval_ids.add(ev.id)
        changed = True

    reports = FeedbackReport.query.order_by(FeedbackReport.generated_at.desc()).all()
    for report in reports:
        ev = report.evaluation
        if not ev:
            continue

        gen_at = report.generated_at.isoformat() if report.generated_at else "unknown"
        report_key = f"feedback-report:{report.id}:{gen_at}"
        if report_key not in existing_log_keys:
            record_audit_log(
                action="feedback_report_generated",
                entity_type="report",
                user_id=ev.job.recruiter.user_id if ev.job and ev.job.recruiter else None,
                details={
                    "source_key": report_key,
                    "evaluation_id": ev.id,
                    "candidate_id": ev.candidate_id,
                    "job_id": ev.job_id,
                    "candidate_name": ev.candidate.user.full_name if ev.candidate and ev.candidate.user else None,
                    "job_title": ev.job.title if ev.job else None,
                },
                created_at=report.generated_at,
            )
            existing_log_keys.add(report_key)
            changed = True

        fairness_key = f"fairness-report:{report.id}:{gen_at}"
        risk = _bias_risk_from_assessment(report.fairness_assessment)
        summary = _bias_summary_from_assessment(report.fairness_assessment)
        if fairness_key not in existing_log_keys:
            record_audit_log(
                action="fairness_assessment_generated",
                entity_type="bias_report",
                user_id=ev.job.recruiter.user_id if ev.job and ev.job.recruiter else None,
                details={
                    "source_key": fairness_key,
                    "evaluation_id": ev.id,
                    "risk_level": risk,
                    "summary": summary,
                },
                created_at=report.generated_at,
            )
            existing_log_keys.add(fairness_key)
            changed = True

        if risk in ("medium", "high") and not _assessment_is_fallback(report.fairness_assessment):
            description = (
                f"Evaluation #{ev.id} for {ev.candidate.user.full_name if ev.candidate and ev.candidate.user else 'candidate'} "
                f"on {ev.job.title if ev.job else 'job'} flagged {risk} bias risk. {summary}"
            )
            alert_key = f"fairness_bias|{description}"
            if alert_key not in existing_alert_keys:
                db.session.add(BiasAlert(
                    bias_type="fairness_bias",
                    severity=risk,
                    description=description,
                    created_at=report.generated_at or datetime.utcnow(),
                ))
                existing_alert_keys.add(alert_key)
                changed = True

    if changed:
        db.session.commit()


def _cleanup_admin_artifact_duplicates():
    changed = False

    logs = AuditLog.query.order_by(AuditLog.id.asc()).all()
    seen_log_keys: set[str] = set()
    for log in logs:
        details = log.details or {}
        source_key = details.get("source_key") if isinstance(details, dict) else None
        dedupe_key = source_key or f"{log.action}|{log.entity_type}|{log.user_id}|{log.created_at.isoformat() if log.created_at else ''}|{details}"
        if dedupe_key in seen_log_keys:
            db.session.delete(log)
            changed = True
        else:
            seen_log_keys.add(dedupe_key)

    alerts = BiasAlert.query.order_by(BiasAlert.id.asc()).all()
    seen_alert_keys: set[str] = set()
    for alert in alerts:
        dedupe_key = f"{alert.bias_type}|{alert.severity}|{alert.description}"
        if _assessment_is_fallback(alert.description):
            db.session.delete(alert)
            changed = True
            continue
        if dedupe_key in seen_alert_keys:
            db.session.delete(alert)
            changed = True
        else:
            seen_alert_keys.add(dedupe_key)

    if changed:
        db.session.commit()

@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})

@api_bp.get("/agents")
def agents():
    return jsonify({"agents": DEFAULT_AGENTS})

@api_bp.get("/regions")
def list_regions():
    regions = Region.query.filter_by(is_active=True).order_by(Region.name).all()
    return jsonify({"regions": [region_to_dict(r) for r in regions]})


@api_bp.get("/admin/stats")
@login_required
def admin_stats(user):
    err = _admin_only(user)
    if err:
        return err
    _cleanup_admin_artifact_duplicates()
    _sync_admin_artifacts()

    total_users = User.query.count()
    total_candidates = User.query.filter_by(role="candidate").count()
    total_recruiters = User.query.filter_by(role="recruiter").count()
    total_evaluations = CandidateJobEvaluation.query.count()
    unresolved_bias_alerts = BiasAlert.query.filter_by(is_resolved=False).count()
    security_events_7d = _security_event_query().count()
    active_reports = AuditLog.query.filter(AuditLog.entity_type.ilike("%report%")).count()
    flagged_hirings = sum(
        1 for ev in CandidateJobEvaluation.query.filter_by(recruiter_action="rejected").all()
        if _is_meaningful_nd_inclusion(ev.nd_inclusion)
    )

    avg_evaluation_score = db.session.query(db.func.avg(CandidateJobEvaluation.score)).scalar() or 0
    total_with_final_action = CandidateJobEvaluation.query.filter(
        CandidateJobEvaluation.recruiter_action.in_(("shortlisted", "rejected"))
    ).count()
    shortlisted_count = CandidateJobEvaluation.query.filter_by(recruiter_action="shortlisted").count()
    shortlist_rate = round((shortlisted_count / total_with_final_action) * 100, 1) if total_with_final_action else 0

    return jsonify({
        "total_users": total_users,
        "total_candidates": total_candidates,
        "total_recruiters": total_recruiters,
        "total_evaluations": total_evaluations,
        "flagged_hirings": flagged_hirings,
        "active_reports": active_reports,
        "security_events_7d": security_events_7d,
        "bias_alerts": unresolved_bias_alerts,
        "avg_evaluation_score": round(float(avg_evaluation_score), 1) if avg_evaluation_score else 0,
        "shortlist_rate": shortlist_rate,
    })


@api_bp.get("/admin/users")
@login_required
def admin_users(user):
    err = _admin_only(user)
    if err:
        return err

    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [admin_user_to_dict(row) for row in users]})


@api_bp.patch("/admin/users/<int:user_id>/status")
@login_required
def admin_update_user_status(user, user_id):
    err = _admin_only(user)
    if err:
        return err

    target = db.session.get(User, user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    if target.id == user.id:
        return jsonify({"error": "You cannot deactivate your own superadmin account"}), 400

    if hasattr(target, "is_active"):
        data = request.get_json(silent=True) or {}
        target.is_active = bool(data.get("is_active", True))
        _record_audit_log(
            action="user_status_updated",
            entity_type="user",
            user_id=user.id,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            details={"target_user_id": target.id, "is_active": target.is_active},
        )
        db.session.commit()

    return jsonify({"user": admin_user_to_dict(target)})


@api_bp.patch("/admin/users/<int:user_id>")
@login_required
def admin_update_user(user, user_id):
    err = _admin_only(user)
    if err:
        return err

    target = db.session.get(User, user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    next_role = data.get("role")
    next_name = data.get("full_name")

    if next_name is not None:
        next_name = str(next_name).strip()
        if not next_name:
            return jsonify({"error": "full_name cannot be empty"}), 400
        target.full_name = next_name

    if next_role is not None:
        if next_role not in ("candidate", "recruiter", "superadmin"):
            return jsonify({"error": "Invalid role"}), 400
        if target.id == user.id and next_role != "superadmin":
            return jsonify({"error": "You cannot change your own superadmin role"}), 400

        target.role = next_role

        # Preserve existing profile data. If the target role needs a profile, ensure it exists.
        if next_role == "candidate" and not target.candidate:
            db.session.add(Candidate(user_id=target.id, skills=[], links=[]))
        elif next_role == "recruiter" and not target.recruiter:
            db.session.add(Recruiter(user_id=target.id))

    _record_audit_log(
        action="user_updated",
        entity_type="user",
        user_id=user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        details={"target_user_id": target.id, "full_name": target.full_name, "role": target.role},
    )
    db.session.commit()
    return jsonify({"user": admin_user_to_dict(target)})


@api_bp.delete("/admin/users/<int:user_id>")
@login_required
def admin_delete_user(user, user_id):
    err = _admin_only(user)
    if err:
        return err

    target = db.session.get(User, user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    if target.id == user.id:
        return jsonify({"error": "You cannot delete your own superadmin account"}), 400

    _record_audit_log(
        action="user_deleted",
        entity_type="user",
        user_id=user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        details={"target_user_id": target.id, "email": target.email, "role": target.role},
    )
    db.session.delete(target)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/admin/audit-logs")
@login_required
def admin_audit_logs(user):
    err = _admin_only(user)
    if err:
        return err

    # Pull latest security logins, reports, and bias activity from DB before returning.
    _sync_admin_artifacts()

    limit = min(request.args.get("limit", default=100, type=int) or 100, 500)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify({"logs": [audit_log_to_dict(log) for log in logs]})


@api_bp.get("/admin/bias-alerts")
@login_required
def admin_bias_alerts(user):
    err = _admin_only(user)
    if err:
        return err

    _sync_admin_artifacts()

    alerts = BiasAlert.query.order_by(BiasAlert.is_resolved.asc(), BiasAlert.created_at.desc()).all()
    return jsonify({"alerts": [bias_alert_to_dict(alert) for alert in alerts]})


@api_bp.get("/admin/reports")
@login_required
def admin_reports(user):
    err = _admin_only(user)
    if err:
        return err

    _sync_admin_artifacts()

    reports = FeedbackReport.query.order_by(FeedbackReport.generated_at.desc()).all()
    return jsonify({"reports": [_report_to_admin_dict(report) for report in reports]})


@api_bp.patch("/admin/bias-alerts/<int:alert_id>/resolve")
@login_required
def admin_resolve_bias_alert(user, alert_id):
    err = _admin_only(user)
    if err:
        return err

    alert = db.session.get(BiasAlert, alert_id)
    if not alert:
        return jsonify({"error": "Bias alert not found"}), 404

    alert.is_resolved = True
    _record_audit_log(
        action="bias_alert_resolved",
        entity_type="bias_alert",
        user_id=user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        details={"alert_id": alert.id, "bias_type": alert.bias_type, "severity": alert.severity},
    )
    db.session.commit()
    return jsonify({"alert": bias_alert_to_dict(alert)})


# ── Profile ──────────────────────────────────────────────────────────────────

@api_bp.get("/me/profile")
@login_required
def get_my_profile(user):
    if user.role == "candidate":
        return jsonify({"profile": candidate_to_dict(user.candidate, include_sensitive=True)})
    return jsonify({"profile": recruiter_to_dict(user.recruiter)})

@api_bp.put("/me/profile")
@login_required
def update_my_profile(user):
    data = request.get_json(silent=True) or {}
    if user.role == "candidate":
        profile = user.candidate or Candidate(user_id=user.id)
        _apply_candidate_profile_data(profile, data)
        github_changed = leetcode_changed = False
        if "github_username" in data:
            new = (data["github_username"] or "").strip() or None
            if new != profile.github_username:
                profile.github_username = new; github_changed = True
        if "leetcode_username" in data:
            new = (data["leetcode_username"] or "").strip() or None
            if new != profile.leetcode_username:
                profile.leetcode_username = new; leetcode_changed = True
        db.session.add(profile); db.session.commit()
        if github_changed or leetcode_changed:
            profile.enrichment_status = "pending"; db.session.commit()
            from agents import enrich_candidate_async
            from app import app as flask_app
            enrich_candidate_async(flask_app, profile.id,
                profile.github_username or "", profile.leetcode_username or "", "")
        return jsonify({"profile": candidate_to_dict(profile, include_sensitive=True)})
    elif user.role == "recruiter":
        profile = user.recruiter or Recruiter(user_id=user.id)
        if "company_name" in data: profile.company_name = data["company_name"]
        if "job_title" in data: profile.job_title = data["job_title"]
        db.session.add(profile); db.session.commit()
        return jsonify({"profile": recruiter_to_dict(profile)})
    return jsonify({"error": "Profile update failed"}), 400

@api_bp.post("/candidate/profile")
@login_required
def update_candidate_profile(user):
    err = _require_role(user, "candidate")
    if err: return err
    data = request.get_json(silent=True) or {}
    profile = user.candidate or Candidate(user_id=user.id)
    _apply_candidate_profile_data(profile, data)
    db.session.add(profile); db.session.commit()
    return jsonify({"profile": candidate_to_dict(profile, include_sensitive=True)})


# ── Enrichment ───────────────────────────────────────────────────────────────

ALLOWED_RESUME_EXT = {"pdf","txt","doc","docx"}

def _allowed_resume(fn):
    return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED_RESUME_EXT

def _extract_resume_text(filepath):
    ext = filepath.rsplit(".",1)[-1].lower()
    try:
        if ext == "txt":
            with open(filepath,"r",errors="ignore") as f: return f.read()
        if ext == "pdf":
            try:
                import pypdf
                r = pypdf.PdfReader(filepath)
                return "\n".join(p.extract_text() or "" for p in r.pages)
            except ImportError: return ""
        if ext in ("doc","docx"):
            try:
                import docx
                d = docx.Document(filepath)
                return "\n".join(p.text for p in d.paragraphs)
            except ImportError: return ""
    except Exception: pass
    return ""

@api_bp.post("/me/profile/enrich")
@login_required
def enrich_profile(user):
    err = _require_role(user, "candidate")
    if err: return err
    candidate = user.candidate
    if not candidate:
        candidate = Candidate(user_id=user.id, skills=[], links=[])
        db.session.add(candidate); db.session.flush()
    github_username  = (request.form.get("github_username")  or "").strip()
    leetcode_username = (request.form.get("leetcode_username") or "").strip()
    if github_username:  candidate.github_username  = github_username
    if leetcode_username: candidate.leetcode_username = leetcode_username
    resume_text = ""
    resume_file = request.files.get("resume")
    if resume_file and resume_file.filename:
        if not _allowed_resume(resume_file.filename):
            return jsonify({"error": "Resume must be PDF, TXT, DOC, or DOCX"}), 400
        filename = secure_filename(f"resume_{user.id}_{resume_file.filename}")
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        resume_file.save(filepath)
        candidate.resume_url = f"/uploads/{filename}"
        resume_text = _extract_resume_text(filepath)
    candidate.enrichment_status = "pending"
    db.session.commit()
    from agents import enrich_candidate_async
    from app import app as flask_app
    enrich_candidate_async(flask_app, candidate.id,
        github_username or candidate.github_username or "",
        leetcode_username or candidate.leetcode_username or "",
        resume_text)
    return jsonify({"ok": True, "message": "Enrichment started.", "enrichment_status": "pending"})

@api_bp.get("/me/profile/enrichment-status")
@login_required
def enrichment_status(user):
    err = _require_role(user, "candidate")
    if err: return err
    c = user.candidate
    if not c: return jsonify({"enrichment_status": "none"})
    return jsonify({
        "enrichment_status":    c.enrichment_status,
        "enrichment_error":     c.enrichment_error,
        "enriched_at":          c.enriched_at.isoformat() if c.enriched_at else None,
        "agent_statuses":       c.agent_statuses or {},
        "github_repos":         c.github_repos,
        "github_stars":         c.github_stars,
        "github_forks":         c.github_forks,
        "github_top_languages": c.github_top_languages or [],
        "github_repos_data":    c.github_repos_data or [],
        "lc_easy":              c.lc_easy,
        "lc_medium":            c.lc_medium,
        "lc_hard":              c.lc_hard,
        "lc_rating":            c.lc_rating,
        "resume_skills":        c.resume_skills or [],
        "resume_projects":      c.resume_projects or [],
        "top_job_matches":      c.top_job_matches or [],
    })


# ── Jobs ─────────────────────────────────────────────────────────────────────

# ── Voice Interview Integration ──────────────────────────────────────────────

def _get_job_category_file(job_category: str) -> str | None:
    """Map job category to the appropriate JSON file path (relative to repo root)."""
    category_map = {
        "blue-collar": "real_voice_bot/Blue-collar-Trades.json",
        "polytechnic": "real_voice_bot/Polytechnic-Skilled-Roles.json",
        "semi-skilled": "real_voice_bot/Semi-Skilled-Workforce.json",
    }
    return category_map.get((job_category or "").lower())


# ── Role classification ───────────────────────────────────────────────────────

_SOFTWARE_ROLE_KEYWORDS = {
    "engineer", "developer", "programmer", "architect", "devops", "sre",
    "frontend", "backend", "fullstack", "full stack", "full-stack",
    "software", "web", "mobile", "android", "ios", "data scientist",
    "data engineer", "ml engineer", "machine learning", "ai engineer",
    "cloud engineer", "platform engineer", "site reliability",
    "react", "node", "python", "java", "golang", "rust", "typescript",
    "infrastructure", "security engineer", "qa engineer", "test engineer",
    "embedded", "firmware", "systems engineer",
}

def _is_software_role(job_title: str, job_description: str = "") -> bool:
    """Return True if the role is a software/tech engineering role."""
    combined = (job_title + " " + job_description[:300]).lower()
    return any(kw in combined for kw in _SOFTWARE_ROLE_KEYWORDS)


def _get_role_domain(job_title: str, skills: list) -> str:
    """Classify the role into a specific engineering domain for prompt targeting."""
    title_lower = job_title.lower()
    skills_lower = " ".join(s.lower() for s in (skills or []))
    combined = title_lower + " " + skills_lower

    if any(k in combined for k in ("frontend", "front-end", "react", "vue", "angular", "css", "ui engineer")):
        return "frontend"
    if any(k in combined for k in ("backend", "back-end", "api", "django", "flask", "spring", "node", "express", "fastapi")):
        return "backend"
    if any(k in combined for k in ("fullstack", "full stack", "full-stack")):
        return "fullstack"
    if any(k in combined for k in ("devops", "sre", "site reliability", "kubernetes", "docker", "ci/cd", "terraform", "cloud")):
        return "devops"
    if any(k in combined for k in ("machine learning", "ml", "ai engineer", "data scientist", "nlp", "deep learning", "pytorch", "tensorflow")):
        return "ml"
    if any(k in combined for k in ("data engineer", "spark", "airflow", "etl", "pipeline", "warehouse")):
        return "data_engineering"
    if any(k in combined for k in ("android", "ios", "mobile", "flutter", "react native", "swift", "kotlin")):
        return "mobile"
    if any(k in combined for k in ("security", "penetration", "appsec", "devsecops")):
        return "security"
    if any(k in combined for k in ("embedded", "firmware", "rtos", "microcontroller")):
        return "embedded"
    return "software_general"


_DOMAIN_FOCUS_AREAS = {
    "frontend": [
        "React & Component Architecture", "State Management", "Performance Optimization",
        "Accessibility & WCAG", "TypeScript", "CSS & Layout", "SSR/CSR/ISR",
        "Browser APIs & Web Platform", "Testing (Jest/RTL/Cypress)", "Build Tooling",
    ],
    "backend": [
        "API Design (REST/GraphQL)", "Database Design & Optimization", "Authentication & Authorization",
        "Caching Strategies", "Concurrency & Async", "Microservices & Architecture",
        "Message Queues", "Error Handling & Observability", "Security Best Practices", "Scalability",
    ],
    "fullstack": [
        "React & Frontend Architecture", "REST API Design", "Database Modeling",
        "Authentication Flows", "State Management", "Performance (FE + BE)",
        "Deployment & CI/CD", "TypeScript", "Testing Strategy", "System Design",
    ],
    "devops": [
        "Container Orchestration (Kubernetes)", "CI/CD Pipeline Design", "Infrastructure as Code",
        "Observability & Monitoring", "Cloud Architecture (AWS/GCP/Azure)", "Networking & Security",
        "Incident Response", "GitOps", "Cost Optimization", "Service Mesh",
    ],
    "ml": [
        "Model Training & Evaluation", "Feature Engineering", "Overfitting & Regularization",
        "Transformer Architecture", "Vector Databases & Embeddings", "MLOps & Deployment",
        "Inference Optimization", "Data Pipelines", "Experiment Tracking", "LLM Fine-tuning",
    ],
    "data_engineering": [
        "ETL/ELT Pipeline Design", "Spark & Distributed Processing", "Data Warehouse Modeling",
        "Streaming (Kafka/Flink)", "Data Quality & Lineage", "Orchestration (Airflow/Prefect)",
        "SQL Optimization", "Cloud Data Platforms", "Schema Evolution", "Partitioning Strategies",
    ],
    "mobile": [
        "Activity/View Lifecycle", "State Management (mobile)", "Memory Management",
        "Offline-first Architecture", "Push Notifications", "Performance Profiling",
        "Navigation Patterns", "Platform APIs", "Testing on Device", "App Store Deployment",
    ],
    "security": [
        "OWASP Top 10", "Authentication & OAuth2", "Cryptography Fundamentals",
        "Threat Modeling", "Secure Code Review", "Penetration Testing Methodology",
        "Secrets Management", "Zero Trust Architecture", "Incident Response", "Compliance",
    ],
    "embedded": [
        "RTOS Concepts", "Memory Management (bare metal)", "Interrupt Handling",
        "Communication Protocols (I2C/SPI/UART)", "Power Optimization", "Debugging with JTAG",
        "Bootloader Design", "Peripheral Drivers", "Real-time Constraints", "Safety Standards",
    ],
    "software_general": [
        "Data Structures & Algorithms", "System Design", "Object-Oriented Design",
        "Concurrency & Threading", "Database Fundamentals", "API Design",
        "Testing & TDD", "Code Quality & Refactoring", "Version Control & Git", "Problem Solving",
    ],
}


def _generate_interview_questions(job_context: dict, candidate_context: dict, evaluation_gaps: list) -> list:
    """
    Generate 5 role-aware, JD-aware, resume-aware interview questions using Groq.

    For software engineering roles: uses a domain-specific Groq prompt that
    explicitly forbids vocational/trade topics and generates FAANG-quality
    technical questions tailored to the JD, candidate skills, and gaps.

    For non-software roles: falls back to the existing JSON-based loader.
    """
    job_title = job_context.get("title", "")
    job_description = job_context.get("description", "")
    candidate_skills = candidate_context.get("skills", [])
    candidate_name = candidate_context.get("name", "")
    years_exp = candidate_context.get("years_experience", 0)
    trade = candidate_context.get("trade", job_title)

    # ── Route: non-software roles use the existing JSON loader ──────────────
    if not _is_software_role(job_title, job_description):
        try:
            import sys
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            voice_bot_root = os.path.join(repo_root, "real_voice_bot")
            for p in (repo_root, voice_bot_root):
                if p not in sys.path:
                    sys.path.insert(0, p)
            original_cwd = os.getcwd()
            os.chdir(voice_bot_root)
            try:
                from real_voice_bot.nodes.utils import load_questions_for_trade
                questions_raw = load_questions_for_trade(trade)
            finally:
                os.chdir(original_cwd)
            formatted = []
            for i, q in enumerate(questions_raw[:5]):
                formatted.append({
                    "id": i + 1,
                    "question": q["question"],
                    "focus_area": q["topic"],
                    "ideal_answer": q.get("ideal_answer", ""),
                })
            if formatted:
                return formatted
        except Exception as e:
            current_app.logger.warning(f"[Interview] JSON loader failed for '{trade}': {e}")
        # Fall through to Groq if JSON loader fails

    # ── Route: software roles → Groq-powered generation ─────────────────────
    domain = _get_role_domain(job_title, candidate_skills)
    focus_areas = _DOMAIN_FOCUS_AREAS.get(domain, _DOMAIN_FOCUS_AREAS["software_general"])

    # Pick 5 focus areas: prioritise gaps, then skills, then domain defaults
    gap_areas = [g for g in (evaluation_gaps or []) if g]
    skill_areas = [s for s in (candidate_skills or []) if s]

    # Build a prioritised list of focus areas for this specific candidate
    priority_areas = []
    for gap in gap_areas[:2]:
        priority_areas.append(f"Probe gap: {gap}")
    for skill in skill_areas[:3]:
        priority_areas.append(f"Depth-test skill: {skill}")
    # Fill remaining slots from domain defaults
    for area in focus_areas:
        if len(priority_areas) >= 5:
            break
        priority_areas.append(area)
    priority_areas = priority_areas[:5]

    # Truncate JD to avoid token overflow
    jd_snippet = (job_description or "")[:600].strip()
    skills_str = ", ".join(candidate_skills[:15]) if candidate_skills else "not specified"
    gaps_str = ", ".join(evaluation_gaps[:5]) if evaluation_gaps else "none identified"

    # Resume and GitHub context
    resume_summary = (candidate_context.get("resume_summary") or "")[:400].strip()
    resume_projects = candidate_context.get("resume_projects", [])
    resume_projects_str = ""
    if resume_projects:
        proj_lines = []
        for p in resume_projects[:3]:
            if isinstance(p, dict):
                proj_lines.append(f"- {p.get('name', 'Project')}: {p.get('description', '')[:120]}")
        resume_projects_str = "\n".join(proj_lines)

    github_info = candidate_context.get("github_data", {})
    gh_languages = ", ".join(github_info.get("languages", [])[:6])
    gh_repos = github_info.get("top_repos", [])
    gh_repo_str = "; ".join(gh_repos[:3]) if gh_repos else ""
    gh_context = ""
    if gh_languages or gh_repo_str:
        gh_context = f"GitHub: {gh_languages}" + (f" | Repos: {gh_repo_str}" if gh_repo_str else "")

    system_prompt = f"""You are a senior technical interviewer at a top-tier tech company (FAANG-level).
You are conducting a real technical interview for a {job_title} position.

STRICT DOMAIN RULES — you MUST follow these without exception:
- Generate questions ONLY about software engineering, computer science, and technology.
- NEVER generate questions about: HVAC, plumbing, electrical wiring, woodworking, construction,
  manufacturing, welding, carpentry, warehouse operations, safety compliance, mechanical trades,
  or ANY non-software vocational topic.
- If you are unsure whether a topic is software-related, default to software engineering concepts.

INTERVIEW CONTEXT:
- Role: {job_title}
- Domain: {domain.replace('_', ' ').title()}
- Job Description: {jd_snippet if jd_snippet else 'Not provided'}
- Candidate: {candidate_name}, {years_exp} years of experience
- Experience Level: {candidate_context.get('experience_level', 'mid')}
- Candidate Skills: {skills_str}
- Identified Skill Gaps: {gaps_str}

RESUME & PROJECTS:
{resume_projects_str if resume_projects_str else 'Not provided'}
{resume_summary if resume_summary else ''}

{gh_context}

QUESTION QUALITY REQUIREMENTS:
- Sound like a real senior engineer asking, not a textbook
- Reference the candidate's actual skills, projects, or resume experience where possible
- Avoid "What is X?" style questions — ask about application, trade-offs, and real scenarios
- Each question should feel like it belongs in a Google/Meta/Amazon interview
- BAD: "What is React?" GOOD: "You've worked with React — walk me through how you'd optimise a component that re-renders too frequently."
- BAD: "What is a database?" GOOD: "Given your PostgreSQL experience, how would you approach indexing a table with 50M rows that gets heavy read traffic?"

FOCUS AREAS FOR THIS INTERVIEW (in priority order):
{chr(10).join(f'{i+1}. {area}' for i, area in enumerate(priority_areas))}

Generate exactly 5 interview questions. Return ONLY a JSON array:
[
  {{
    "id": 1,
    "question": "<the full interview question>",
    "focus_area": "<topic label, e.g. 'React Performance'>",
    "ideal_answer": "<key points a strong answer should cover, 2-4 sentences>"
  }},
  ...
]

No markdown fences. No explanation. Just the JSON array."""

    try:
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not set")

        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_api_key,
            max_tokens=1800,
            temperature=0.7,
        )
        import re as _re, json as _json
        result = llm.invoke(system_prompt)
        raw = result.content.strip()
        # Strip markdown fences if present
        raw = _re.sub(r"^```(?:json)?\s*", "", raw)
        raw = _re.sub(r"\s*```$", "", raw)
        questions_data = _json.loads(raw)

        if not isinstance(questions_data, list) or len(questions_data) == 0:
            raise ValueError("Empty or invalid question list returned")

        formatted = []
        for i, q in enumerate(questions_data[:5]):
            formatted.append({
                "id": q.get("id", i + 1),
                "question": q.get("question", "").strip(),
                "focus_area": q.get("focus_area", priority_areas[i] if i < len(priority_areas) else "Technical"),
                "ideal_answer": q.get("ideal_answer", "").strip(),
            })
        current_app.logger.info(f"[Interview] Generated {len(formatted)} Groq questions for '{job_title}' ({domain})")
        return formatted

    except Exception as e:
        current_app.logger.error(f"[Interview] Groq question generation failed for '{job_title}': {e}")
        # Deterministic fallback — generic but domain-appropriate, never vocational
        return [
            {"id": 1, "question": f"Walk me through a challenging technical problem you solved in your {job_title} work. What was the problem, your approach, and the outcome?", "focus_area": "Problem Solving", "ideal_answer": "Should describe a real technical challenge with clear problem definition, systematic approach, and measurable outcome."},
            {"id": 2, "question": "How do you approach code reviews? What do you look for, and how do you give constructive feedback?", "focus_area": "Engineering Practices", "ideal_answer": "Should cover correctness, readability, performance, security, and communication style."},
            {"id": 3, "question": "Describe a time you had to make a significant architectural decision. What trade-offs did you consider?", "focus_area": "System Design", "ideal_answer": "Should demonstrate awareness of scalability, maintainability, cost, and team constraints."},
            {"id": 4, "question": "How do you ensure the quality and reliability of the code you ship?", "focus_area": "Testing & Quality", "ideal_answer": "Should mention unit/integration/e2e tests, CI/CD, monitoring, and code review practices."},
            {"id": 5, "question": "Tell me about a time you had to learn a new technology quickly for a project. How did you approach it?", "focus_area": "Learning Agility", "ideal_answer": "Should show structured learning approach, ability to apply knowledge quickly, and self-awareness."},
        ]


def _assess_interview_answer(question: dict, answer: str, candidate_context: dict) -> dict:
    """
    Score a candidate's interview answer using Groq.

    For software engineering roles: uses a senior-engineer scoring rubric covering
    technical depth, clarity, system thinking, and communication.

    For non-software roles: uses the existing real_voice_bot technical_score_node.
    """
    trade = candidate_context.get("trade", "")
    is_sw = _is_software_role(trade)

    # ── Software engineering scoring via Groq ────────────────────────────────
    if is_sw:
        return _assess_software_answer(question, answer, candidate_context)

    # ── Non-software: use existing real_voice_bot node ───────────────────────
    try:
        import sys, types
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        voice_bot_root = os.path.join(repo_root, "real_voice_bot")
        for p in (repo_root, voice_bot_root):
            if p not in sys.path:
                sys.path.insert(0, p)

        if "database" not in sys.modules:
            stub = types.ModuleType("database")
            stub.save_result = lambda *a, **kw: None          # type: ignore[attr-defined]
            stub.check_integrity_flag = lambda scores, avg: False  # type: ignore[attr-defined]
            sys.modules["database"] = stub

        original_cwd = os.getcwd()
        os.chdir(voice_bot_root)
        try:
            import importlib
            nodes_tech = importlib.import_module("nodes.technical")
            technical_score_node = nodes_tech.technical_score_node
        finally:
            os.chdir(original_cwd)

        state = {
            "phase": "technical_listen",
            "candidate_info": {
                "name": candidate_context.get("name", "Candidate"),
                "trade": trade,
                "years_of_experience": str(candidate_context.get("years_of_experience", 0)),
            },
            "messages": [{"role": "assistant", "content": question.get("question", "")}],
            "questions": [{
                "topic": question.get("focus_area", "General"),
                "question": question.get("question", ""),
                "ideal_answer": question.get("ideal_answer", ""),
            }],
            "question_index": 0,
            "scores": [],
            "weak_topics": [],
            "awaiting_followup": False,
            "followup_count": 0,
            "pending_score": None,
            "last_user_input": answer,
            "last_response": "",
            "result_saved": False,
            "saved_result_id": None,
        }

        result = technical_score_node(state)
        scores = result.get("scores", [])
        score = scores[-1] if scores else 5
        sentiment = "positive" if score >= 8 else ("neutral" if score >= 5 else "negative")
        last_response = result.get("last_response", "")
        key_point = last_response if last_response else f"Scored {score}/10 on {question.get('focus_area', 'this topic')}"
        follow_up_hint = ""
        if result.get("awaiting_followup"):
            follow_up_hint = last_response
        elif score >= 8:
            follow_up_hint = "Strong answer — well done."
        elif score >= 5:
            follow_up_hint = "Good start. Try to add a specific example next time."
        else:
            follow_up_hint = "Review this topic and practise with a concrete example."

        return {
            "score": score,
            "sentiment": sentiment,
            "key_point": key_point[:200],
            "follow_up_hint": follow_up_hint[:200],
        }

    except Exception as e:
        current_app.logger.error(f"[Interview] technical_score_node failed: {e}")
        return _assess_software_answer(question, answer, candidate_context)  # graceful fallback


def _assess_software_answer(question: dict, answer: str, candidate_context: dict) -> dict:
    """
    Score a software engineering interview answer using a senior-engineer rubric.
    Returns: { score, sentiment, key_point, follow_up_hint, feedback,
               technical_depth, clarity, system_thinking, communication }
    """
    import re as _re, json as _json

    trade = candidate_context.get("trade", "Software Engineer")
    years_exp = candidate_context.get("years_of_experience", candidate_context.get("years_experience", 0))
    focus_area = question.get("focus_area", "Technical")
    q_text = question.get("question", "")
    ideal = question.get("ideal_answer", "")

    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        current_app.logger.warning("[Interview] GROQ_API_KEY not set — using default score")
        return {"score": 5, "sentiment": "neutral", "key_point": "Answer received.", "follow_up_hint": "Thank you for your response.", "feedback": ""}

    score_prompt = f"""You are a senior software engineering interviewer at a top-tier tech company.
You are scoring a candidate's answer to a technical interview question.

ROLE: {trade}
EXPERIENCE: {years_exp} years
TOPIC: {focus_area}
QUESTION: {q_text}
IDEAL ANSWER KEY POINTS: {ideal if ideal else 'Use your expert judgment'}

CANDIDATE'S ANSWER:
"{answer}"

SCORING RUBRIC (score 0-10):
- 9-10: Exceptional — demonstrates deep expertise, mentions trade-offs, gives concrete examples, shows system-level thinking
- 7-8: Strong — covers the key concepts correctly, some depth, minor gaps
- 5-6: Adequate — understands the basics but lacks depth, missing important nuances
- 3-4: Weak — partial understanding, significant gaps or misconceptions
- 1-2: Poor — mostly incorrect or off-topic
- 0: No answer or completely irrelevant

DIMENSION SCORES (each 1-10):
- technical_depth: How technically accurate and deep is the answer?
- clarity: How clearly and concisely is the answer communicated?
- system_thinking: Does the candidate think about trade-offs, scale, and real-world constraints?
- communication: Is the answer well-structured and easy to follow?

IMPORTANT:
- Be fair but rigorous. A vague answer that name-drops buzzwords without substance scores 3-4.
- A concise, accurate answer with a real example scores 7-8.
- Only give 9-10 for genuinely impressive answers that show mastery.
- Consider the experience level: {years_exp} years. Expect more depth from senior candidates.

Return ONLY a JSON object:
{{
  "score": <integer 0-10>,
  "technical_depth": <integer 1-10>,
  "clarity": <integer 1-10>,
  "system_thinking": <integer 1-10>,
  "communication": <integer 1-10>,
  "strength": "<one sentence: what the candidate got right>",
  "gap": "<one sentence: the most important thing missing, empty if score >= 8>",
  "feedback": "<2-3 sentences of constructive interviewer feedback>",
  "follow_up": "<a natural follow-up question to probe deeper, empty if score >= 8>"
}}

No markdown. Just JSON."""

    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_api_key,
            max_tokens=500,
            temperature=0.1,  # low temp for consistent scoring
        )
        result = llm.invoke(score_prompt)
        raw = result.content.strip()
        raw = _re.sub(r"^```(?:json)?\s*", "", raw)
        raw = _re.sub(r"\s*```$", "", raw)
        data = _json.loads(raw)

        score = max(0, min(10, int(data.get("score", 5))))
        sentiment = "positive" if score >= 7 else ("neutral" if score >= 4 else "negative")
        strength = data.get("strength", "")
        gap = data.get("gap", "")
        feedback = data.get("feedback", "")
        follow_up = data.get("follow_up", "")

        # key_point: most useful single piece of info for the candidate
        key_point = strength if score >= 6 else (gap if gap else feedback)

        # follow_up_hint: actionable next step
        if follow_up and score < 8:
            follow_up_hint = follow_up
        elif score >= 8:
            follow_up_hint = "Excellent answer — strong technical depth shown."
        elif score >= 5:
            follow_up_hint = gap if gap else "Try to add a concrete example or discuss trade-offs."
        else:
            follow_up_hint = gap if gap else "Review this topic and practise explaining it with a real-world example."

        current_app.logger.info(
            f"[Score] {focus_area}: {score}/10 | "
            f"depth={data.get('technical_depth')} clarity={data.get('clarity')} "
            f"system={data.get('system_thinking')} comm={data.get('communication')}"
        )

        return {
            "score": score,
            "sentiment": sentiment,
            "key_point": key_point[:250],
            "follow_up_hint": follow_up_hint[:250],
            "feedback": feedback[:400],
            "technical_depth": data.get("technical_depth", score),
            "clarity": data.get("clarity", score),
            "system_thinking": data.get("system_thinking", score),
            "communication": data.get("communication", score),
        }

    except Exception as e:
        current_app.logger.error(f"[Interview] Groq scoring failed: {e}")
        return {
            "score": 5,
            "sentiment": "neutral",
            "key_point": "Answer received.",
            "follow_up_hint": "Thank you for your response.",
            "feedback": "",
        }

@api_bp.post("/candidate/interviews/start")
@login_required
def start_interview(user):
    """Start a new voice interview session."""
    err = _require_role(user, "candidate")
    if err:
        return err
    
    data = request.get_json(silent=True) or {}
    evaluation_id = data.get("evaluation_id")
    
    if not evaluation_id:
        return jsonify({"error": "evaluation_id is required"}), 400
    
    # Load the evaluation and job
    evaluation = db.session.get(CandidateJobEvaluation, evaluation_id)
    if not evaluation:
        return jsonify({"error": "Evaluation not found"}), 404
    
    if evaluation.candidate.user_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    job = evaluation.job
    candidate = evaluation.candidate
    
    # Determine job category file
    job_category = getattr(job, 'category', 'general')
    category_file = _get_job_category_file(job_category)
    
    # Prepare enriched contexts for role-aware questioning
    # Gather resume data, GitHub data, and skills for richer context
    resume_projects = candidate.resume_projects or []
    resume_summary = candidate.summary or ""
    github_data = {
        "languages": candidate.github_top_languages or [],
        "repos": candidate.github_repos or 0,
        "stars": candidate.github_stars or 0,
        "top_repos": [
            r.get("name", "") for r in (candidate.github_repos_data or [])[:5]
            if isinstance(r, dict)
        ],
    }
    merged_skills = list(set(
        (candidate.skills or []) +
        (candidate.resume_skills or [])
    ))

    # Determine experience level
    exp_years = candidate.years_experience or candidate.resume_years_experience or 0
    if exp_years < 2:
        experience_level = "junior"
    elif exp_years < 5:
        experience_level = "mid"
    elif exp_years < 10:
        experience_level = "senior"
    else:
        experience_level = "lead"

    job_context = {
        "title": job.title,
        "description": job.description or "",
        "category": job_category,
        "skills_required": job.skills_required or []
    }

    candidate_context = {
        "name": candidate.user.full_name,
        "years_experience": exp_years,
        "experience_level": experience_level,
        "skills": merged_skills,
        "trade": job.title,
        "resume_summary": resume_summary,
        "resume_projects": resume_projects[:5],
        "github_data": github_data,
    }
    
    # Generate interview questions (includes ideal_answer for server-side scoring)
    questions_full = _generate_interview_questions(job_context, candidate_context, evaluation.gaps or [])

    # Strip ideal_answer before sending to frontend
    questions_for_client = [
        {"id": q["id"], "question": q["question"], "focus_area": q["focus_area"]}
        for q in questions_full
    ]

    # Prevent duplicate creation (React StrictMode / double-click / retry).
    # If a "started" interview already exists for this evaluation, return it.
    existing = CandidateInterview.query.filter_by(
        evaluation_id=evaluation.id, status="started"
    ).first()
    if existing:
        existing_questions = [
            {"id": e["id"], "question": e["question"], "focus_area": e["focus_area"]}
            for e in (existing.transcript or [])
        ]
        return jsonify({
            "interview_id": existing.id,
            "questions": existing_questions,
            "job_title": job.title,
            "candidate_name": candidate.user.full_name,
        })

    # Create interview record — store full questions (with ideal_answer) in transcript seed
    interview = CandidateInterview(
        candidate_id=candidate.id,
        evaluation_id=evaluation.id,
        status="started",
        transcript=[
            {"id": q["id"], "question": q["question"], "focus_area": q["focus_area"],
             "ideal_answer": q.get("ideal_answer", "")}
            for q in questions_full
        ],
    )
    db.session.add(interview)
    db.session.commit()

    return jsonify({
        "interview_id": interview.id,
        "questions": questions_for_client,
        "job_title": job.title,
        "candidate_name": candidate.user.full_name,
    })

@api_bp.post("/candidate/interviews/<int:interview_id>/answer")
@login_required
def submit_interview_answer(user, interview_id):
    """Submit an answer to an interview question."""
    err = _require_role(user, "candidate")
    if err:
        return err
    
    data = request.get_json(silent=True) or {}
    question_id = data.get("question_id")
    answer_text = data.get("answer_text", "").strip()
    duration_seconds = data.get("duration_seconds", 0)
    
    if not question_id or not answer_text:
        return jsonify({"error": "question_id and answer_text are required"}), 400
    
    # Load interview
    interview = db.session.get(CandidateInterview, interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    
    if interview.candidate.user_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Find the pre-seeded question entry in transcript
    transcript = list(interview.transcript or [])
    question_entry = next((e for e in transcript if e.get("id") == question_id), None)

    if not question_entry:
        return jsonify({"error": f"question_id {question_id} not found in this interview"}), 400

    # Assess the answer using real_voice_bot technical_score_node
    candidate_context = {
        "name": interview.candidate.user.full_name,
        "trade": interview.evaluation.job.title,
        "years_of_experience": interview.candidate.years_experience or 0,
    }

    assessment = _assess_interview_answer(question_entry, answer_text, candidate_context)

    # Update the entry in-place
    question_entry["answer"] = answer_text
    question_entry["duration_seconds"] = duration_seconds
    question_entry["assessment"] = assessment

    # Replace in transcript list
    interview.transcript = [
        question_entry if e.get("id") == question_id else e
        for e in transcript
    ]
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(interview, "transcript")
    db.session.commit()

    return jsonify({"assessment": assessment})

@api_bp.post("/candidate/interviews/<int:interview_id>/complete")
@login_required
def complete_interview(user, interview_id):
    """Complete an interview session."""
    err = _require_role(user, "candidate")
    if err:
        return err
    
    data = request.get_json(silent=True) or {}
    overall_score = data.get("overall_score")
    duration_seconds = data.get("duration_seconds", 0)
    
    # Load interview
    interview = db.session.get(CandidateInterview, interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    
    if interview.candidate.user_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Calculate overall score if not provided
    if overall_score is None:
        transcript = interview.transcript or []
        scores = [e["assessment"]["score"] for e in transcript if e.get("assessment", {}).get("score") is not None]
        overall_score = round(sum(scores) / len(scores), 2) if scores else 5.0

    interview.status = "completed"
    interview.overall_score = overall_score
    interview.duration_seconds = duration_seconds
    interview.completed_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"success": True})

@api_bp.get("/candidate/interviews/<int:eval_id>")
@login_required
def get_interview_by_evaluation(user, eval_id):
    """Get interview for a specific evaluation."""
    err = _require_role(user, "candidate")
    if err:
        return err
    
    # Find interview by evaluation_id
    interview = CandidateInterview.query.filter_by(evaluation_id=eval_id).first()
    
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    
    if interview.candidate.user_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    return jsonify({
        "interview_id": interview.id,
        "evaluation_id": interview.evaluation_id,
        "status": interview.status,
        "transcript": [
            {k: v for k, v in e.items() if k != "ideal_answer"}
            for e in (interview.transcript or [])
        ],
        "overall_score": interview.overall_score,
        "duration_seconds": interview.duration_seconds,
        "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
        "created_at": interview.created_at.isoformat(),
    })


# ── LiveKit Voice Agent Routes ────────────────────────────────────────────────

@api_bp.post("/livekit/token")
@login_required
def get_livekit_token(user):
    """
    Generate a LiveKit access token for a candidate to join an interview room.
    The room metadata carries all candidate info so the agent can pre-populate state.

    Body: { room_name?, candidate_name, trade, phone_number?, email?, job_id?, user_id? }
    Returns: { token, room_name, ws_url }
    """
    import uuid as _uuid

    try:
        from livekit.api import AccessToken, VideoGrants
    except ImportError:
        return jsonify({"error": "livekit-api package not installed. Run: pip install livekit-api"}), 500

    data = request.get_json(silent=True) or {}
    room_name = data.get("room_name") or f"interview-{_uuid.uuid4().hex[:8]}"

    candidate_name = data.get("candidate_name") or (user.full_name if user else "Candidate")
    trade = data.get("trade", "")
    phone_number = data.get("phone_number", "")
    email = data.get("email", "") or (user.email if user else "")
    job_id = data.get("job_id")
    eval_id = data.get("eval_id")
    user_id = data.get("user_id") or user.id

    # ── Enrich metadata with job and candidate context ──
    job_description = data.get("job_description", "")
    candidate_skills = data.get("candidate_skills", [])
    resume_summary = data.get("resume_summary", "")
    github_data = data.get("github_data", {})
    experience_level = data.get("experience_level", "mid")
    role = data.get("role", "")

    # If eval_id provided, try to load richer context from DB
    if eval_id and not any([job_description, candidate_skills]):
        try:
            evaluation = db.session.get(CandidateJobEvaluation, eval_id)
            if evaluation and evaluation.job and evaluation.candidate:
                cand = evaluation.candidate
                job = evaluation.job
                job_description = job.description or ""
                candidate_skills = list(set(
                    (cand.skills or []) + (cand.resume_skills or [])
                ))
                resume_summary = cand.summary or ""
                github_data = {
                    "languages": cand.github_top_languages or [],
                    "top_repos": [
                        r.get("name", "") for r in (cand.github_repos_data or [])[:5]
                        if isinstance(r, dict)
                    ],
                }
                exp_years = cand.years_experience or cand.resume_years_experience or 0
                if exp_years < 2:
                    experience_level = "junior"
                elif exp_years < 5:
                    experience_level = "mid"
                elif exp_years < 10:
                    experience_level = "senior"
                else:
                    experience_level = "lead"
                role = _get_role_domain(job.title, candidate_skills)
        except Exception:
            pass

    metadata = json.dumps({
        "name": candidate_name,
        "trade": trade,
        "phone_number": phone_number,
        "email": email,
        "job_id": job_id,
        "user_id": user_id,
        "livekit_room": room_name,
        "job_description": job_description,
        "candidate_skills": candidate_skills,
        "resume_summary": resume_summary,
        "github_data": github_data,
        "experience_level": experience_level,
        "role": role,
    })

    livekit_api_key = os.getenv("LIVEKIT_API_KEY", "")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET", "")
    livekit_url = os.getenv("LIVEKIT_URL", "")

    if not livekit_api_key or not livekit_api_secret:
        return jsonify({"error": "LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in .env"}), 500

    try:
        token = (
            AccessToken(
                api_key=livekit_api_key,
                api_secret=livekit_api_secret,
            )
            .with_identity(f"candidate-{user_id}")
            .with_name(candidate_name)
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .with_metadata(metadata)
            .to_jwt()
        )
    except Exception as e:
        current_app.logger.error(f"[LiveKit] Token generation failed: {e}")
        return jsonify({"error": "Failed to generate LiveKit token"}), 500

    # Reuse an existing in-progress session for this evaluation to prevent duplicates
    # (React StrictMode can fire the effect twice in development)
    from models import LiveKitInterview
    candidate_id = user.candidate.id if user.candidate else None
    lk_interview = None
    if eval_id and candidate_id:
        lk_interview = (
            LiveKitInterview.query
            .filter_by(candidate_id=candidate_id, evaluation_id=eval_id, status="started")
            .first()
        )
    if lk_interview:
        # Reuse the existing room so the token stays consistent
        room_name = lk_interview.livekit_room
        # Re-generate token for the same room
        try:
            token = (
                AccessToken(
                    api_key=livekit_api_key,
                    api_secret=livekit_api_secret,
                )
                .with_identity(f"candidate-{user_id}")
                .with_name(candidate_name)
                .with_grants(VideoGrants(room_join=True, room=room_name))
                .with_metadata(metadata)
                .to_jwt()
            )
        except Exception as e:
            current_app.logger.error(f"[LiveKit] Token re-generation failed: {e}")
            return jsonify({"error": "Failed to generate LiveKit token"}), 500
    else:
        lk_interview = LiveKitInterview(
            candidate_id=candidate_id,
            evaluation_id=eval_id,
            livekit_room=room_name,
            phone_number=phone_number,
            trade=trade,
            status="started",
        )
        db.session.add(lk_interview)
        db.session.commit()

    return jsonify({
        "token": token,
        "room_name": room_name,
        "ws_url": livekit_url,
    })


@api_bp.post("/livekit/webhook")
def livekit_webhook():
    """
    Receives LiveKit webhook events.
    On room_finished: marks the LiveKitInterview record as completed.
    No JWT auth — validated by LIVEKIT_WEBHOOK_SECRET if set.
    """
    from models import LiveKitInterview

    # Optional webhook secret validation
    webhook_secret = os.getenv("LIVEKIT_WEBHOOK_SECRET", "")
    if webhook_secret:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or auth_header[7:] != webhook_secret:
            return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    event = data.get("event", "")
    room_info = data.get("room", {})
    room_name = room_info.get("name", "")

    current_app.logger.info(f"[LiveKit Webhook] event={event} room={room_name}")

    if event in ("room_finished", "participant_left") and room_name:
        interview = LiveKitInterview.query.filter_by(livekit_room=room_name).first()
        if interview and interview.status != "completed":
            interview.status = "completed"
            interview.completed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.info(f"[LiveKit Webhook] Marked interview {interview.id} as completed")

    return jsonify({"ok": True})


@api_bp.get("/candidate/livekit-interview/<int:eval_id>")
@login_required
def get_livekit_interview(user, eval_id):
    """
    Returns the LiveKitInterview for this evaluation if it exists.
    Used by frontend to show 'View Interview Results' button.
    """
    from models import LiveKitInterview

    err = _require_role(user, "candidate")
    if err:
        return err

    candidate_id = user.candidate.id if user.candidate else None
    if not candidate_id:
        return jsonify({"error": "Candidate profile not found"}), 404

    # Look up by evaluation_id scoped to this candidate
    interview = (
        LiveKitInterview.query
        .filter_by(candidate_id=candidate_id, evaluation_id=eval_id)
        .order_by(LiveKitInterview.started_at.desc())
        .first()
    )

    if not interview:
        return jsonify({"error": "No LiveKit interview found"}), 404

    return jsonify({
        "id": interview.id,
        "livekit_room": interview.livekit_room,
        "trade": interview.trade,
        "language": interview.language,
        "scores": interview.scores or [],
        "avg_score": interview.avg_score,
        "fitment": interview.fitment,
        "weak_topics": interview.weak_topics or [],
        "feedback": interview.feedback,
        "transcript": interview.transcript or [],
        "status": interview.status,
        "started_at": interview.started_at.isoformat() if interview.started_at else None,
        "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
    })


@api_bp.get("/jobs")
@login_required
def list_jobs(user):
    region_id = request.args.get("region_id", type=int)
    if user.role == "recruiter":
        if not user.recruiter: return jsonify({"jobs": []})
        jobs = Job.query.filter_by(recruiter_id=user.recruiter.id).order_by(Job.created_at.desc()).all()
    else:
        q = Job.query.filter_by(is_active=True)
        if region_id: q = q.filter_by(region_id=region_id)
        elif user.candidate and user.candidate.preferred_region_id:
            q = q.filter_by(region_id=user.candidate.preferred_region_id)
        jobs = q.order_by(Job.created_at.desc()).all()
    return jsonify({"jobs": [job_to_dict(j) for j in jobs]})

@api_bp.post("/jobs")
@login_required
def create_job(user):
    err = _require_role(user, "recruiter")
    if err: return err
    if not user.recruiter: return jsonify({"error": "Recruiter profile not found"}), 400
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title: return jsonify({"error": "title is required"}), 400
    job = Job(
        recruiter_id=user.recruiter.id,
        region_id=data.get("region_id"),
        title=title,
        company=data.get("company") or user.recruiter.company_name or "",
        location=data.get("location",""),
        employment_type=data.get("employment_type","Full-time"),
        description=data.get("description",""),
        requirements=data.get("requirements",[]),
        skills_required=data.get("skills_required",[]),
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        is_active=data.get("is_active",True),
    )
    created_eval_ids: list[int] = []
    try:
        db.session.add(job)
        db.session.flush()
        current_app.logger.info("[JobCreate] recruiter_id=%s job_id=%s title=%s", user.recruiter.id, job.id, job.title)
        link_result = _auto_link_job_candidates(job)
        created_eval_ids = link_result["created_eval_ids"]
        db.session.commit()
        current_app.logger.info(
            "[JobCreate] linked job_id=%s total_candidates=%s created_apps=%s created_evals=%s existing_pairs=%s",
            job.id, link_result["total_candidates"], link_result["created_apps"], link_result["created_evals"], link_result["existing_pairs"]
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception("[JobCreate] transaction failed recruiter_id=%s title=%s", user.recruiter.id, job.title)
        return jsonify({"error": "Failed to create and link job"}), 500
    if created_eval_ids:
        from agents import evaluate_candidate_for_job_async
        from app import app as flask_app
        for eval_id in created_eval_ids:
            evaluate_candidate_for_job_async(flask_app, eval_id)
    return jsonify({"job": job_to_dict(job)}), 201

@api_bp.get("/jobs/<int:job_id>")
@login_required
def get_job(user, job_id):
    job = db.session.get(Job, job_id)
    if not job: return jsonify({"error": "Not found"}), 404
    if user.role == "recruiter" and (not user.recruiter or job.recruiter_id != user.recruiter.id):
        return jsonify({"error": "Forbidden"}), 403
    if user.role == "candidate" and not job.is_active:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"job": job_to_dict(job)})

@api_bp.put("/jobs/<int:job_id>")
@login_required
def update_job(user, job_id):
    err = _require_role(user, "recruiter")
    if err: return err
    job = db.session.get(Job, job_id)
    if not job or not user.recruiter or job.recruiter_id != user.recruiter.id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    for f in ("title","company","location","employment_type","description",
              "requirements","skills_required","salary_min","salary_max","is_active","region_id"):
        if f in data: setattr(job, f, data[f])
    db.session.commit()
    return jsonify({"job": job_to_dict(job)})

@api_bp.get("/admin/jobs/<int:job_id>/inclusion-settings")
@login_required
def get_job_inclusion_settings(user, job_id):
    err = _require_role(user, "recruiter", "superadmin")
    if err: return err
    job = db.session.get(Job, job_id)
    if not job: return jsonify({"error": "Not found"}), 404
    if user.role == "recruiter" and (not user.recruiter or job.recruiter_id != user.recruiter.id):
        return jsonify({"error": "Forbidden"}), 403
    defaults = {
        "enabled": True,
        "nd_detection_sensitivity": "medium",
        "detect_hyperfocus": True,
        "detect_pattern_recognition": True,
        "detect_debugging_consistency": True,
        "apply_score_uplift": True,
        "generate_accessible_summaries": True,
        "flag_underestimation_risks": True,
        "output_format": "standard",
    }
    return jsonify({**defaults, **(job.inclusion_settings or {})})

@api_bp.patch("/admin/jobs/<int:job_id>/inclusion-settings")
@login_required
def update_job_inclusion_settings(user, job_id):
    err = _require_role(user, "recruiter", "superadmin")
    if err: return err
    job = db.session.get(Job, job_id)
    if not job: return jsonify({"error": "Not found"}), 404
    if user.role == "recruiter" and (not user.recruiter or job.recruiter_id != user.recruiter.id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    allowed = {
        "enabled", "nd_detection_sensitivity", "detect_hyperfocus",
        "detect_pattern_recognition", "detect_debugging_consistency",
        "apply_score_uplift", "generate_accessible_summaries",
        "flag_underestimation_risks", "output_format",
    }
    current = dict(job.inclusion_settings or {})
    current.update({k: v for k, v in data.items() if k in allowed})
    job.inclusion_settings = current
    db.session.commit()
    return jsonify(current)

@api_bp.get("/admin/inclusion/status")
@login_required
def get_global_inclusion_status(user):
    err = _require_role(user, "recruiter", "superadmin")
    if err: return err
    return jsonify({"enabled": current_app.config.get("INCLUSION_ENABLED", True)})

@api_bp.post("/admin/inclusion/toggle")
@login_required
def toggle_global_inclusion(user):
    err = _require_role(user, "recruiter", "superadmin")
    if err: return err
    data = request.get_json(silent=True) or {}
    current_app.config["INCLUSION_ENABLED"] = bool(data.get("enabled", False))
    return jsonify({"enabled": current_app.config["INCLUSION_ENABLED"]})

@api_bp.delete("/jobs/<int:job_id>")
@login_required
def delete_job(user, job_id):
    err = _require_role(user, "recruiter")
    if err: return err
    job = db.session.get(Job, job_id)
    if not job or not user.recruiter or job.recruiter_id != user.recruiter.id:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(job); db.session.commit()
    return jsonify({"ok": True})


# ── Applications ─────────────────────────────────────────────────────────────

@api_bp.post("/jobs/<int:job_id>/apply")
@login_required
def apply_to_job(user, job_id):
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"error": "Candidate profile not found"}), 400
    job = db.session.get(Job, job_id)
    if not job or not job.is_active: return jsonify({"error": "Job not found"}), 404
    existing = Application.query.filter_by(job_id=job_id, candidate_id=user.candidate.id).first()
    if existing: return jsonify({"error": "Already applied to this job"}), 409
    data = request.get_json(silent=True) or {}
    app_ = Application(job_id=job_id, candidate_id=user.candidate.id,
                       cover_letter=data.get("cover_letter",""), status="applied")
    db.session.add(app_); db.session.flush()
    _push_notification(job.recruiter.user.id, "application_received",
        f"New application: {user.full_name}", f"{user.full_name} applied for {job.title}",
        "/dashboard/candidates")
    db.session.commit()
    return jsonify({"application": application_to_dict(app_)}), 201

@api_bp.get("/me/applications")
@login_required
def my_applications(user):
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"applications": []})
    apps = Application.query.filter_by(candidate_id=user.candidate.id).order_by(Application.created_at.desc()).all()
    return jsonify({"applications": [application_to_dict(a, include_job=True) for a in apps]})

@api_bp.get("/jobs/<int:job_id>/applications")
@login_required
def list_applications_for_job(user, job_id):
    err = _require_role(user, "recruiter")
    if err: return err
    job = db.session.get(Job, job_id)
    if not job or not user.recruiter or job.recruiter_id != user.recruiter.id:
        return jsonify({"error": "Not found"}), 404
    apps = Application.query.filter_by(job_id=job_id).order_by(Application.created_at.desc()).all()
    return jsonify({"applications": [application_to_dict(a, include_candidate=True) for a in apps]})

@api_bp.patch("/applications/<int:app_id>/status")
@login_required
def update_application_status(user, app_id):
    err = _require_role(user, "recruiter")
    if err: return err
    app_ = db.session.get(Application, app_id)
    if not app_: return jsonify({"error": "Not found"}), 404
    if not user.recruiter or app_.job.recruiter_id != user.recruiter.id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    old_status = app_.status
    if "status" in data:
        if data["status"] not in ("applied","in_review","shortlisted","rejected","on_hold"):
            return jsonify({"error": "Invalid status"}), 400
        app_.status = data["status"]
        if app_.status == "shortlisted": app_.is_shortlisted = True
    if "is_shortlisted" in data:
        app_.is_shortlisted = bool(data["is_shortlisted"])
        if app_.is_shortlisted: app_.status = "shortlisted"
    for f in ("match_score","confidence","strengths","gaps","why_fit","feedback_note"):
        if f in data: setattr(app_, f, data[f])
    if app_.status != old_status:
        labels = {"in_review":"In Review","shortlisted":"Shortlisted 🎉","rejected":"Not selected","on_hold":"On Hold"}
        _push_notification(app_.candidate.user.id, "status_changed",
            f"Application update: {app_.job.title}",
            f"Your application status changed to {labels.get(app_.status, app_.status)}",
            "/candidate/applications")
    db.session.commit()
    return jsonify({"application": application_to_dict(app_)})


# ── Messages ─────────────────────────────────────────────────────────────────

@api_bp.get("/me/messages")
@login_required
def my_messages(user):
    msgs = Message.query.filter(
        (Message.sender_id == user.id) | (Message.recipient_id == user.id)
    ).order_by(Message.created_at.desc()).all()
    return jsonify({"messages": [message_to_dict(m, viewer_id=user.id) for m in msgs]})

@api_bp.post("/messages")
@login_required
def send_message(user):
    data = request.get_json(silent=True) or {}
    recipient_id = data.get("recipient_id")
    body = (data.get("body") or "").strip()
    subject = (data.get("subject") or "New Message").strip()
    if not recipient_id or not body:
        return jsonify({"error": "recipient_id and body are required"}), 400
    recipient = db.session.get(User, recipient_id)
    if not recipient: return jsonify({"error": "Recipient not found"}), 404
    msg = Message(sender_id=user.id, recipient_id=recipient_id,
                  application_id=data.get("application_id"), subject=subject, body=body)
    db.session.add(msg); db.session.flush()
    _push_notification(recipient_id, "message_received",
        f"New message from {user.full_name}", body[:120],
        "/candidate/messages" if recipient.role == "candidate" else "/dashboard/messages")
    try:
        from email_service import send_message_notification
        send_message_notification(recipient_email=recipient.email,
            recipient_name=recipient.full_name, sender_name=user.full_name,
            message_subject=subject, message_body=body)
    except Exception as e:
        current_app.logger.warning("Email notification failed: %s", e)
    db.session.commit()
    return jsonify({"message": message_to_dict(msg, viewer_id=user.id)}), 201

@api_bp.patch("/messages/<int:msg_id>/read")
@login_required
def mark_message_read(user, msg_id):
    msg = db.session.get(Message, msg_id)
    if not msg or msg.recipient_id != user.id: return jsonify({"error": "Not found"}), 404
    msg.is_read = True; db.session.commit()
    return jsonify({"ok": True})

# ── Notifications ─────────────────────────────────────────────────────────────

@api_bp.get("/me/notifications")
@login_required
def my_notifications(user):
    notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(50).all()
    unread = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({"notifications": [notification_to_dict(n) for n in notifs], "unread_count": unread})

@api_bp.patch("/me/notifications/read-all")
@login_required
def mark_all_notifications_read(user):
    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})

@api_bp.patch("/me/notifications/<int:notif_id>/read")
@login_required
def mark_notification_read(user, notif_id):
    notif = db.session.get(Notification, notif_id)
    if not notif or notif.user_id != user.id: return jsonify({"error": "Not found"}), 404
    notif.is_read = True; db.session.commit()
    return jsonify({"ok": True})


# ── Job Alerts ───────────────────────────────────────────────────────────────

@api_bp.get("/jobs/alerts")
@login_required
def get_job_alerts(user):
    """Candidate: get new job matches since last login."""
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"alerts": [], "total": 0})
    since = user.last_login_at
    q = JobAlert.query.filter_by(candidate_id=user.candidate.id)
    if since:
        q = q.filter(JobAlert.alerted_at >= since)
    alerts = q.order_by(JobAlert.alerted_at.desc()).limit(50).all()
    return jsonify({
        "alerts": [{
            "id": a.id,
            "match_score": a.match_score,
            "alerted_at": a.alerted_at.isoformat(),
            "job": scraped_job_to_dict(a.scraped_job) if a.scraped_job else None,
        } for a in alerts],
        "total": len(alerts),
    })


@api_bp.post("/jobs/alert/subscribe")
@login_required
def toggle_alert_subscription(user):
    """Candidate: toggle real-time job alerts on/off."""
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"error": "Candidate profile not found"}), 400
    data = request.get_json(silent=True) or {}
    sub = AlertSubscription.query.filter_by(candidate_id=user.candidate.id).first()
    if not sub:
        sub = AlertSubscription(candidate_id=user.candidate.id)
        db.session.add(sub)
    if "enabled" in data:
        sub.enabled = bool(data["enabled"])
    if "min_match_score" in data:
        sub.min_match_score = max(0, min(100, int(data["min_match_score"])))
    db.session.commit()
    return jsonify({"subscription": {"enabled": sub.enabled, "min_match_score": sub.min_match_score}})


@api_bp.get("/jobs/alert/subscription")
@login_required
def get_alert_subscription(user):
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"subscription": None})
    sub = AlertSubscription.query.filter_by(candidate_id=user.candidate.id).first()
    if not sub:
        return jsonify({"subscription": {"enabled": False, "min_match_score": 30}})
    return jsonify({"subscription": {"enabled": sub.enabled, "min_match_score": sub.min_match_score}})


# ── Scraped Jobs ──────────────────────────────────────────────────────────────

@api_bp.get("/scraped-jobs")
@login_required
def list_scraped_jobs(user):
    q         = (request.args.get("q") or "").strip().lower()
    region_id = request.args.get("region_id", type=int)
    limit     = min(int(request.args.get("limit", 50)), 200)
    query = ScrapedJob.query.filter_by(is_active=True)
    if q:
        query = query.filter(db.or_(ScrapedJob.title.ilike(f"%{q}%"), ScrapedJob.company.ilike(f"%{q}%")))
    if region_id:
        query = query.filter_by(region_id=region_id)
    elif user.role == "candidate" and user.candidate and user.candidate.preferred_region_id:
        query = query.filter_by(region_id=user.candidate.preferred_region_id)
    jobs = query.order_by(ScrapedJob.scraped_at.desc()).limit(limit).all()
    return jsonify({"jobs": [scraped_job_to_dict(j) for j in jobs], "total": len(jobs)})

@api_bp.post("/scraped-jobs/refresh")
@login_required
def refresh_scraped_jobs(user):
    err = _require_role(user, "recruiter")
    if err: return err
    from scraper import scrape_once
    from app import app as flask_app
    import threading
    threading.Thread(target=scrape_once, args=(flask_app,), daemon=True).start()
    return jsonify({"ok": True, "message": "Scrape triggered in background"})

# ── Evaluations ───────────────────────────────────────────────────────────────

@api_bp.post("/evaluate")
@login_required
def evaluate_candidate(user):
    err = _require_role(user, "recruiter")
    if err: return err
    if not user.recruiter: return jsonify({"error": "Recruiter profile not found"}), 400
    data = request.get_json(silent=True) or {}
    candidate_id = data.get("candidate_id")
    job_id = data.get("job_id")
    if not candidate_id or not job_id:
        return jsonify({"error": "candidate_id and job_id are required"}), 400
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate: return jsonify({"error": "Candidate not found"}), 404
    job = db.session.get(Job, job_id)
    if not job: return jsonify({"error": "Job not found"}), 404
    if job.recruiter_id != user.recruiter.id: return jsonify({"error": "Forbidden"}), 403
    try:
        app_, ev, _ = _ensure_application_and_evaluation_for_pair(job, candidate)
        if ev:
            app_.status = app_.status or "applied"
            app_.is_shortlisted = bool(ev.recruiter_action == "shortlisted")
        ev.eval_status = "pending"; ev.eval_error = None; ev.score = None
        ev.recommendation = "PENDING"; ev.strengths = []; ev.gaps = []; ev.why_fit = None; ev.nd_inclusion = {}; ev.evaluated_at = None
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("[Evaluate] failed candidate_id=%s job_id=%s", candidate_id, job_id)
        return jsonify({"error": "Failed to start evaluation"}), 500
    from agents import evaluate_candidate_for_job_async
    from app import app as flask_app
    evaluate_candidate_for_job_async(flask_app, ev.id)
    return jsonify({"evaluation": evaluation_to_dict(ev, include_candidate=True)}), 202

@api_bp.get("/evaluations")
@login_required
def list_evaluations(user):
    err = _require_role(user, "recruiter")
    if err: return err
    if not user.recruiter: return jsonify({"evaluations": [], "total": 0})
    job_id = request.args.get("job_id", type=int)
    if not job_id: return jsonify({"error": "job_id query param is required"}), 400
    job = db.session.get(Job, job_id)
    if not job or job.recruiter_id != user.recruiter.id: return jsonify({"error": "Job not found"}), 404
    q = CandidateJobEvaluation.query.filter_by(job_id=job_id)
    if request.args.get("action"): q = q.filter_by(recruiter_action=request.args.get("action"))
    evs = q.order_by(CandidateJobEvaluation.score.desc().nullslast(), CandidateJobEvaluation.created_at.desc()).all()
    return jsonify({"evaluations": [evaluation_to_dict(ev, include_candidate=True) for ev in evs],
                    "total": len(evs), "job": job_to_dict(job)})

@api_bp.get("/evaluations/<int:eval_id>")
@login_required
def get_evaluation(user, eval_id):
    err = _require_role(user, "recruiter")
    if err: return err
    ev = db.session.get(CandidateJobEvaluation, eval_id)
    if not ev: return jsonify({"error": "Not found"}), 404
    if not user.recruiter or ev.job.recruiter_id != user.recruiter.id:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({"evaluation": evaluation_to_dict(ev, include_candidate=True)})

@api_bp.post("/evaluations/<int:eval_id>/action")
@login_required
def update_evaluation_action(user, eval_id):
    err = _require_role(user, "recruiter")
    if err: return err
    ev = db.session.get(CandidateJobEvaluation, eval_id)
    if not ev: return jsonify({"error": "Not found"}), 404
    if not user.recruiter or ev.job.recruiter_id != user.recruiter.id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("shortlisted","rejected","pending"):
        return jsonify({"error": "action must be shortlisted, rejected, or pending"}), 400
    ev.recruiter_action = action
    ev.action_taken_at = datetime.now(timezone.utc) if action != "pending" else None
    db.session.commit()
    if action == "shortlisted":
        _push_notification(ev.candidate.user.id, "shortlisted",
            f"You've been shortlisted for {ev.job.title}!",
            f"A recruiter shortlisted you for: {ev.job.title}", "/candidate/applications")
    elif action == "rejected":
        _push_notification(ev.candidate.user.id, "status_changed",
            f"Application update: {ev.job.title}",
            f"Your evaluation for {ev.job.title} was not selected.", "/candidate/applications")
    db.session.commit()
    return jsonify({"evaluation": evaluation_to_dict(ev, include_candidate=True, include_job=True)})

@api_bp.post("/recruiter/action")
@login_required
def recruiter_action(user):
    """
    Update recruiter action for a candidate-job evaluation.
    
    POST /api/recruiter/action
    {
      "candidate_id": int,
      "job_id": int,
      "action": "shortlist" | "reject" | "reset"
    }
    
    Returns: 200 with updated evaluation, 404 if not found, 403 if forbidden
    """
    err = _require_role(user, "recruiter")
    if err: return err
    data = request.get_json(silent=True) or {}
    candidate_id = data.get("candidate_id")
    job_id = data.get("job_id")
    action = data.get("action")
    
    if not all([candidate_id, job_id, action]):
        return jsonify({"error": "candidate_id, job_id, action required"}), 400
    if action not in ("shortlist", "reject", "reset"):
        return jsonify({"error": "action must be 'shortlist', 'reject', or 'reset'"}), 400
    
    ev = CandidateJobEvaluation.query.filter_by(candidate_id=candidate_id, job_id=job_id).first()
    if not ev:
        return jsonify({"error": "Evaluation not found"}), 404
    
    if not user.recruiter or ev.job.recruiter_id != user.recruiter.id:
        return jsonify({"error": "Forbidden"}), 403
    
    # Map action to recruiter_action value
    action_map = {"shortlist": "shortlisted", "reject": "rejected", "reset": "pending"}
    old_action = ev.recruiter_action
    ev.recruiter_action = action_map[action]
    ev.action_taken_at = datetime.now(timezone.utc) if action != "reset" else None
    db.session.commit()
    
    # Send notification to candidate
    if action == "shortlist":
        _push_notification(
            ev.candidate.user.id,
            "shortlisted",
            f"You've been shortlisted for {ev.job.title}!",
            f"A recruiter shortlisted you for: {ev.job.title}",
            "/candidate/applications"
        )
    elif action == "reject":
        _push_notification(
            ev.candidate.user.id,
            "status_changed",
            f"Application update: {ev.job.title}",
            f"Your evaluation for {ev.job.title} was not selected.",
            "/candidate/applications"
        )
    
    db.session.commit()
    return jsonify({"evaluation": evaluation_to_dict(ev, include_candidate=True, include_job=True)}), 200


# ── Candidate evaluations (candidate-facing) ──────────────────────────────────

@api_bp.get("/candidate/evaluations")
@login_required
def candidate_evaluations(user):
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"evaluations": []})
    evs = CandidateJobEvaluation.query.filter_by(candidate_id=user.candidate.id).order_by(CandidateJobEvaluation.created_at.desc()).all()
    return jsonify({"evaluations": [evaluation_to_dict(ev, include_job=True) for ev in evs]})

@api_bp.get("/candidate/evaluations/<int:eval_id>")
@login_required
def get_candidate_evaluation(user, eval_id):
    """
    Get a single evaluation for the candidate.
    Used for polling to check if evaluation is complete.
    """
    err = _require_role(user, "candidate")
    if err: return err
    ev = db.session.get(CandidateJobEvaluation, eval_id)
    if not ev or not user.candidate or ev.candidate_id != user.candidate.id:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"evaluation": evaluation_to_dict(ev, include_job=True)}), 200

@api_bp.post("/jobs/<int:job_id>/express-interest")
@login_required
def express_interest(user, job_id):
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"error": "Candidate profile not found"}), 400
    job = db.session.get(Job, job_id)
    if not job or not job.is_active: return jsonify({"error": "Job not found"}), 404
    try:
        app_, ev, created = _ensure_application_and_evaluation_for_pair(job, user.candidate)
        if not created and ev:
            return jsonify({"evaluation": evaluation_to_dict(ev, include_job=True)}), 200
        _push_notification(job.recruiter.user.id, "application_received",
            f"{user.full_name} expressed interest in {job.title}", "AI evaluation queued.",
            f"/dashboard/candidates")
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("[ExpressInterest] failed candidate_id=%s job_id=%s", user.candidate.id, job_id)
        return jsonify({"error": "Failed to express interest"}), 500
    from agents import evaluate_candidate_for_job_async
    from app import app as flask_app
    evaluate_candidate_for_job_async(flask_app, ev.id)
    return jsonify({"evaluation": evaluation_to_dict(ev, include_job=True)}), 202

@api_bp.delete("/candidate/evaluations/<int:eval_id>")
@login_required
def withdraw_application(user, eval_id):
    err = _require_role(user, "candidate")
    if err: return err
    ev = db.session.get(CandidateJobEvaluation, eval_id)
    if not ev: return jsonify({"error": "Not found"}), 404
    if not user.candidate or ev.candidate_id != user.candidate.id:
        return jsonify({"error": "Forbidden"}), 403
    db.session.delete(ev); db.session.commit()
    return jsonify({"message": "Withdrawn"}), 200

# ── Feedback ──────────────────────────────────────────────────────────────────

@api_bp.get("/evaluations/<int:eval_id>/feedback")
@login_required
def get_feedback_report(user, eval_id):
    from models import FeedbackReport
    ev = db.session.get(CandidateJobEvaluation, eval_id)
    if not ev: return jsonify({"error": "Not found"}), 404
    if user.role == "candidate":
        if not user.candidate or ev.candidate_id != user.candidate.id:
            return jsonify({"error": "Forbidden"}), 403
    elif user.role == "recruiter":
        if not user.recruiter or ev.job.recruiter_id != user.recruiter.id:
            return jsonify({"error": "Forbidden"}), 403
    report = FeedbackReport.query.filter_by(evaluation_id=eval_id).first()
    if not report: return jsonify({"error": "Feedback report not yet generated"}), 404
    if user.role == "candidate":
        return jsonify({
            "candidate_report": report.candidate_report,
            "learning_resources": report.learning_resources or {},
            "task_checklist": report.task_checklist or [],
            "nd_inclusion": ev.nd_inclusion or None,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        })
    return jsonify({
        "recruiter_summary": report.recruiter_summary,
        "interview_questions": report.interview_questions or [],
        "fairness_assessment": report.fairness_assessment,
        "learning_resources": report.learning_resources or {},
        "task_checklist": report.task_checklist or [],
        "nd_inclusion": public_nd_inclusion(ev.nd_inclusion),
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "generation_time_ms": report.generation_time_ms,
    })


# ── Learning Path API ────────────────────────────────────────────────────────

@api_bp.patch("/learning/check/<task_id>")
@login_required
def check_learning_task(user, task_id):
    """Update task completion status in learning path."""
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"error": "Candidate profile not found"}), 400

    # Find the feedback report containing this task
    from models import FeedbackReport
    reports = FeedbackReport.query.join(CandidateJobEvaluation).filter(
        CandidateJobEvaluation.candidate_id == user.candidate.id
    ).all()

    for report in reports:
        checklist = report.task_checklist or []
        for task in checklist:
            if task.get("id") == task_id:
                task["completed"] = not task.get("completed", False)
                report.task_checklist = checklist
                db.session.commit()
                return jsonify({"task": task}), 200

    return jsonify({"error": "Task not found"}), 404

@api_bp.get("/learning/hub")
@login_required
def get_learning_hub(user):
    """Get all learning paths across evaluations for the candidate."""
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"error": "Candidate profile not found"}), 400

    from models import FeedbackReport
    reports = FeedbackReport.query.join(CandidateJobEvaluation).filter(
        CandidateJobEvaluation.candidate_id == user.candidate.id
    ).order_by(FeedbackReport.generated_at.desc()).all()

    hub_data = []
    for report in reports:
        if report.learning_resources and report.task_checklist:
            hub_data.append({
                "evaluation_id": report.evaluation_id,
                "job_title": report.evaluation.job.title,
                "company": report.evaluation.job.company,
                "generated_at": report.generated_at.isoformat(),
                "learning_resources": report.learning_resources,
                "task_checklist": report.task_checklist,
                "completed_tasks": sum(1 for t in report.task_checklist if t.get("completed")),
                "total_tasks": len(report.task_checklist)
            })

    return jsonify({"learning_paths": hub_data})


# ── AI Chat API ──────────────────────────────────────────────────────────────

@api_bp.post("/chat/ask")
@login_required
def ask_chat_question(user):
    """Stream AI response to candidate questions about their evaluation."""
    err = _require_role(user, "candidate")
    if err: return err
    if not user.candidate: return jsonify({"error": "Candidate profile not found"}), 400

    data = request.get_json()
    candidate_id = data.get("candidate_id")
    job_id = data.get("job_id")
    question = data.get("question")

    if not all([candidate_id, job_id, question]):
        return jsonify({"error": "Missing required fields: candidate_id, job_id, question"}), 400

    if candidate_id != user.candidate.id:
        return jsonify({"error": "Forbidden"}), 403

    # Get evaluation and feedback report
    ev = CandidateJobEvaluation.query.filter_by(
        candidate_id=candidate_id, job_id=job_id
    ).first()
    if not ev:
        return jsonify({"error": "Evaluation not found"}), 404

    report = ev.feedback_report
    if not report:
        return jsonify({"error": "Feedback report not yet generated"}), 404

    # Prepare context for Groq
    context = f"""
JOB: {ev.job.title} at {ev.job.company}
SCORE: {ev.score}/100
RECOMMENDATION: {ev.recommendation}

STRENGTHS: {', '.join(ev.strengths or [])}
GAPS: {', '.join(ev.gaps or [])}
WHY FIT: {ev.why_fit}

FEEDBACK REPORT:
{report.candidate_report}

LEARNING RESOURCES:
{json.dumps(report.learning_resources, indent=2)}

QUESTION: {question}
"""

    def generate_response():
        try:
            from groq import Groq
            groq_key = os.getenv("GROQ_API_KEY", "")
            if not groq_key:
                yield "data: Error: Groq API key not configured\n\n"
                return

            client = Groq(api_key=groq_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful career coach answering questions about a candidate's job evaluation. Be encouraging, specific, and actionable. Use the provided context to give accurate answers."},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=1024,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield f"data: {chunk.choices[0].delta.content}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return Response(generate_response(), mimetype="text/event-stream")


# ── Job matching ──────────────────────────────────────────────────────────────

def _skill_overlap_score(candidate_skills, job_tags):
    if not candidate_skills or not job_tags: return 0
    c = {s.lower() for s in candidate_skills}
    j = {t.lower() for t in job_tags}
    return min(100, round(len(c & j) / max(len(j), 1) * 100))

@api_bp.get("/me/job-matches")
@login_required
def my_job_matches(user):
    err = _require_role(user, "candidate")
    if err: return err
    c = user.candidate
    if not c: return jsonify({"matches": []})
    top_n = min(int(request.args.get("top", 3)), 20)
    all_skills = list({*(c.skills or []), *(c.resume_skills or [])})
    scraped = ScrapedJob.query.filter_by(is_active=True).all()
    scored = sorted([((_skill_overlap_score(all_skills, j.tags or []), j)) for j in scraped],
                    key=lambda x: x[0], reverse=True)
    return jsonify({"matches": [{**scraped_job_to_dict(j), "match_score": s} for s, j in scored[:top_n]]})

@api_bp.get("/recruiter/candidates/<int:candidate_id>/job-matches")
@login_required
def candidate_job_matches(user, candidate_id):
    err = _require_role(user, "recruiter")
    if err: return err
    c = db.session.get(Candidate, candidate_id)
    if not c: return jsonify({"error": "Not found"}), 404
    top_n = min(int(request.args.get("top", 3)), 20)
    all_skills = list({*(c.skills or []), *(c.resume_skills or [])})
    scraped = ScrapedJob.query.filter_by(is_active=True).all()
    scored = sorted([(_skill_overlap_score(all_skills, j.tags or []), j) for j in scraped],
                    key=lambda x: x[0], reverse=True)
    return jsonify({"matches": [{**scraped_job_to_dict(j), "match_score": s} for s, j in scored[:top_n]]})

# ── Recruiter dashboard ───────────────────────────────────────────────────────

@api_bp.get("/recruiter/candidates")
@login_required
def recruiter_candidates(user):
    err = _require_role(user, "recruiter")
    if err: return err
    if not user.recruiter: return jsonify({"candidates": [], "total": 0})
    job_ids = [j.id for j in user.recruiter.jobs]
    if not job_ids: return jsonify({"candidates": [], "total": 0})
    touched = False
    for job_id in job_ids:
        job = db.session.get(Job, job_id)
        if not job:
            continue
        res = _auto_link_job_candidates(job)
        if res["created_apps"] or res["created_evals"]:
            touched = True
    if touched:
        db.session.commit()
    q = Application.query.filter(Application.job_id.in_(job_ids))
    if request.args.get("job_id"): q = q.filter_by(job_id=int(request.args.get("job_id")))
    if request.args.get("status"): q = q.filter_by(status=request.args.get("status"))
    if request.args.get("shortlisted"):
        q = q.filter_by(is_shortlisted=request.args.get("shortlisted").lower() == "true")
    apps = q.order_by(Application.match_score.desc().nullslast(), Application.created_at.desc()).all()
    # Attach latest evaluation (if any) for each application so frontend can act on evaluations
    out = []
    for a in apps:
        app_d = application_to_dict(a, include_candidate=True, include_job=True)
        ev = CandidateJobEvaluation.query.filter_by(candidate_id=a.candidate_id, job_id=a.job_id)
        ev = ev.order_by(CandidateJobEvaluation.evaluated_at.desc()).first()
        app_d["latest_evaluation"] = evaluation_to_dict(ev, include_job=True) if ev else None
        # For backward compatibility expose top-level fields similar to previous candidate view
        if app_d["latest_evaluation"]:
            app_d["latest_evaluation"]["score"] = app_d["latest_evaluation"].get("score")
        out.append(app_d)
    return jsonify({"candidates": out, "total": len(out)})

@api_bp.get("/jobs/<int:job_id>/candidates")
@login_required
def list_job_candidates(user, job_id):
    err = _require_role(user, "recruiter")
    if err: return err
    job = db.session.get(Job, job_id)
    if not job or not user.recruiter or job.recruiter_id != user.recruiter.id:
        return jsonify({"error": "Not found"}), 404
    try:
        res = _auto_link_job_candidates(job)
        if res["created_apps"] or res["created_evals"]:
            current_app.logger.info(
                "[JobCandidates] healed job_id=%s created_apps=%s created_evals=%s",
                job_id, res["created_apps"], res["created_evals"]
            )
            db.session.commit()
        apps = Application.query.filter_by(job_id=job_id).order_by(Application.created_at.desc()).all()
        out = []
        for a in apps:
            d = application_to_dict(a, include_candidate=True, include_job=True)
            ev = CandidateJobEvaluation.query.filter_by(candidate_id=a.candidate_id, job_id=a.job_id).first()
            d["latest_evaluation"] = evaluation_to_dict(ev, include_job=True) if ev else None
            out.append(d)
        return jsonify({"candidates": out, "total": len(out)})
    except Exception:
        db.session.rollback()
        current_app.logger.exception("[JobCandidates] failed for job_id=%s", job_id)
        return jsonify({"error": "Failed to fetch job candidates"}), 500

@api_bp.get("/candidates")
@login_required
def list_all_candidates(user):
    err = _require_role(user, "recruiter")
    if err: return err
    skill_filter = request.args.get("skill","").strip().lower()
    min_score = request.args.get("min_score", type=int)
    action_filter = request.args.get("recruiter_action","").lower()
    limit = min(int(request.args.get("limit", 100)), 500)
    candidates = Candidate.query.all()
    results = []
    for c in candidates:
        if skill_filter:
            all_skills = [s.lower() for s in (c.skills or []) + (c.resume_skills or [])]
            if skill_filter not in all_skills: continue
        latest_eval = (CandidateJobEvaluation.query.filter_by(candidate_id=c.id)
            .filter(CandidateJobEvaluation.eval_status == "done")
            .order_by(CandidateJobEvaluation.evaluated_at.desc()).first())
        if latest_eval:
            if min_score is not None and (latest_eval.score is None or latest_eval.score < min_score): continue
            if action_filter and latest_eval.recruiter_action != action_filter: continue
        row = {
            "id": c.id, "user_id": c.user_id,
            "full_name": c.user.full_name if c.user else "Unknown",
            "email": c.user.email if c.user else None,
            "headline": c.headline, "location": c.location,
            "years_experience": c.years_experience,
            "skills": c.skills or [], "resume_skills": c.resume_skills or [],
            "github_username": c.github_username, "github_repos": c.github_repos,
            "github_stars": c.github_stars, "lc_easy": c.lc_easy,
            "lc_medium": c.lc_medium, "lc_hard": c.lc_hard,
            "top_skill": ((c.skills or c.resume_skills or ["N/A"])[0]),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "latest_evaluation": {
                "id": latest_eval.id, "job_id": latest_eval.job_id,
                "job_title": latest_eval.job.title, "job_company": latest_eval.job.company,
                "score": latest_eval.score, "recommendation": latest_eval.recommendation,
                "recruiter_action": latest_eval.recruiter_action,
                "strengths": latest_eval.strengths or [], "gaps": latest_eval.gaps or [],
                "why_fit": latest_eval.why_fit,
                "evaluated_at": latest_eval.evaluated_at.isoformat() if latest_eval.evaluated_at else None,
            } if latest_eval else None,
        }
        results.append(row)
    results.sort(key=lambda x: (x["latest_evaluation"]["score"] if x["latest_evaluation"] and x["latest_evaluation"]["score"] is not None else -1), reverse=True)
    return jsonify({"candidates": results[:limit], "total": len(results)})

@api_bp.get("/candidates/<int:candidate_id>/full")
@login_required
def get_candidate_full_profile(user, candidate_id):
    err = _require_role(user, "recruiter")
    if err: return err
    c = db.session.get(Candidate, candidate_id)
    if not c: return jsonify({"error": "Not found"}), 404
    from models import FeedbackReport
    evs = CandidateJobEvaluation.query.filter_by(candidate_id=candidate_id).order_by(CandidateJobEvaluation.evaluated_at.desc()).all()
    touched = False
    eval_data = []
    for ev in evs:
        touched = _ensure_cultural_dna(ev) or touched
        d = evaluation_to_dict(ev, include_job=True)
        report = FeedbackReport.query.filter_by(evaluation_id=ev.id).first()
        if report:
            d["feedback_report"] = {"recruiter_summary": report.recruiter_summary,
                "interview_questions": report.interview_questions or [],
                "fairness_assessment": report.fairness_assessment,
                "nd_inclusion": public_nd_inclusion(ev.nd_inclusion),
                "generated_at": report.generated_at.isoformat() if report.generated_at else None}
        eval_data.append(d)
    if touched:
        db.session.commit()
    return jsonify({"candidate": candidate_to_dict(c), "evaluations": eval_data, "total_evaluations": len(evs)})


# ── Voice Interview ───────────────────────────────────────────────────────────

@api_bp.post("/candidate/interviews")
@login_required
def save_interview(user):
    """Save a completed voice interview session."""
    err = _require_role(user, "candidate")
    if err:
        return err

    candidate = user.candidate
    if not candidate:
        return jsonify({"error": "Candidate profile not found"}), 404

    data = request.get_json(silent=True) or {}
    evaluation_id   = data.get("evaluation_id")
    questions       = data.get("questions", [])
    answers         = data.get("answers", [])
    assessments     = data.get("assessments", [])
    overall_score   = data.get("overall_score")
    duration_seconds = data.get("duration_seconds")
    completed_at_str = data.get("completed_at")

    if not evaluation_id:
        return jsonify({"error": "evaluation_id is required"}), 400

    # Verify the evaluation belongs to this candidate
    ev = db.session.get(CandidateJobEvaluation, evaluation_id)
    if not ev or ev.candidate_id != candidate.id:
        return jsonify({"error": "Evaluation not found"}), 404

    # Build transcript array
    transcript = []
    for i, q in enumerate(questions):
        transcript.append({
            "id":         q.get("id", i + 1),
            "question":   q.get("question", ""),
            "focus_area": q.get("focus_area", ""),
            "answer":     answers[i] if i < len(answers) else "",
            "assessment": assessments[i] if i < len(assessments) else {},
        })

    completed_at = datetime.utcnow()
    if completed_at_str:
        try:
            completed_at = datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
        except Exception:
            pass

    from models import CandidateInterview
    interview = CandidateInterview(
        candidate_id=candidate.id,
        evaluation_id=evaluation_id,
        transcript=transcript,
        overall_score=overall_score,
        duration_seconds=duration_seconds,
        completed_at=completed_at,
    )
    db.session.add(interview)
    db.session.commit()

    return jsonify({
        "ok": True,
        "interview": {
            "id":              interview.id,
            "evaluation_id":   interview.evaluation_id,
            "overall_score":   interview.overall_score,
            "duration_seconds": interview.duration_seconds,
            "completed_at":    interview.completed_at.isoformat(),
        },
    }), 201


@api_bp.get("/candidate/interviews/<int:evaluation_id>")
@login_required
def get_interview(user, evaluation_id):
    """Get the most recent interview for a given evaluation."""
    err = _require_role(user, "candidate")
    if err:
        return err

    candidate = user.candidate
    if not candidate:
        return jsonify({"error": "Candidate profile not found"}), 404

    from models import CandidateInterview
    interview = (
        CandidateInterview.query
        .filter_by(candidate_id=candidate.id, evaluation_id=evaluation_id)
        .order_by(CandidateInterview.completed_at.desc())
        .first()
    )

    if not interview:
        return jsonify({"interview": None}), 200

    return jsonify({
        "interview": {
            "id":              interview.id,
            "evaluation_id":   interview.evaluation_id,
            "transcript":      interview.transcript or [],
            "overall_score":   interview.overall_score,
            "duration_seconds": interview.duration_seconds,
            "completed_at":    interview.completed_at.isoformat(),
        },
    })
