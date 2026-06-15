from __future__ import annotations

from models import (
    Application,
    AuditLog,
    BiasAlert,
    Candidate,
    CandidateJobEvaluation,
    Job,
    Message,
    Notification,
    Recruiter,
    ScrapedJob,
    User,
)


def iso(value):
    return value.isoformat() if value else None


def region_to_dict(region) -> dict | None:
    if region is None:
        return None
    return {
        "id": region.id,
        "name": region.name,
        "code": region.code,
        "is_active": region.is_active,
    }


# ─────────────────────────── core profiles ──────────────────────────────────

def candidate_to_dict(candidate: Candidate | None, include_sensitive: bool = False) -> dict | None:
    if candidate is None:
        return None
    data = {
        "id": candidate.id,
        "user_id": candidate.user_id,
        "full_name": candidate.user.full_name if candidate.user else None,
        "email": candidate.user.email if candidate.user else None,
        "headline": candidate.headline,
        "location": candidate.location,
        "summary": candidate.summary,
        "years_experience": candidate.years_experience,
        "skills": candidate.skills or [],
        "links": candidate.links or [],
        "projects": candidate.projects or [],
        # enrichment
        "github_username": candidate.github_username,
        "leetcode_username": candidate.leetcode_username,
        "resume_url": candidate.resume_url,
        "github_repos": candidate.github_repos,
        "github_stars": candidate.github_stars,
        "github_forks": getattr(candidate, "github_forks", None),
        "github_top_languages": candidate.github_top_languages or [],
        "github_repos_data": getattr(candidate, "github_repos_data", None) or [],
        "lc_easy": candidate.lc_easy,
        "lc_medium": candidate.lc_medium,
        "lc_hard": candidate.lc_hard,
        "lc_rating": candidate.lc_rating,
        "resume_skills": candidate.resume_skills or [],
        "resume_projects": getattr(candidate, "resume_projects", None) or [],
        "enrichment_status": candidate.enrichment_status,
        "enrichment_error": candidate.enrichment_error,
        "agent_statuses": candidate.agent_statuses or {},
        "top_job_matches": candidate.top_job_matches or [],
        "preferred_region": region_to_dict(candidate.preferred_region) if candidate.preferred_region else None,
        "enriched_at": iso(candidate.enriched_at),
        "created_at": iso(candidate.created_at),
        "updated_at": iso(candidate.updated_at),
    }
    if include_sensitive:
        data["neurodivergent"] = candidate.neurodivergent
        data["nd_type"] = candidate.nd_type
    return data


def recruiter_to_dict(recruiter: Recruiter | None) -> dict | None:
    if recruiter is None:
        return None
    return {
        "id": recruiter.id,
        "user_id": recruiter.user_id,
        "full_name": recruiter.user.full_name if recruiter.user else None,
        "email": recruiter.user.email if recruiter.user else None,
        "company_name": recruiter.company_name,
        "job_title": recruiter.job_title,
        "created_at": iso(recruiter.created_at),
        "updated_at": iso(recruiter.updated_at),
    }


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "auth_provider": user.auth_provider,
        "created_at": iso(user.created_at),
        "last_login_at": iso(user.last_login_at),
        "candidate": candidate_to_dict(user.candidate, include_sensitive=True) if user.role == "candidate" else None,
        "recruiter": recruiter_to_dict(user.recruiter) if user.role == "recruiter" else None,
    }


def admin_user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": iso(user.created_at),
        "last_login_at": iso(user.last_login_at),
        # The current schema does not persist an active flag on User.
        # Keep the admin UI functional by treating users as active by default.
        "is_active": bool(getattr(user, "is_active", True)),
    }


def public_nd_inclusion(nd_inclusion: dict | None) -> dict | None:
    if not nd_inclusion:
        return None
    source = nd_inclusion.get("nd_source") or nd_inclusion.get("source") or "inferred"
    return {
        "nd_flag": bool(nd_inclusion.get("nd_flag")),
        "nd_source": source,
        "nd_type": "anonymized" if nd_inclusion.get("nd_flag") else None,
        "risk_of_underestimation": nd_inclusion.get("risk_of_underestimation"),
        "recommended_action": nd_inclusion.get("recommended_action"),
        "penalty_reduction_weight": nd_inclusion.get("penalty_reduction_weight"),
        "strengths_detected": nd_inclusion.get("strengths_detected") or [],
        "underestimation_risks": nd_inclusion.get("underestimation_risks") or [],
    }


# ─────────────────────────── job ────────────────────────────────────────────

def job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "recruiter_id": job.recruiter_id,
        "region": region_to_dict(job.region) if job.region else None,
        "company": job.company,
        "company_name": job.recruiter.company_name if job.recruiter else job.company,
        "title": job.title,
        "location": job.location,
        "employment_type": job.employment_type,
        "description": job.description,
        "requirements": job.requirements or [],
        "skills_required": job.skills_required or [],
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "is_active": job.is_active,
        "application_count": len(job.applications),
        "created_at": iso(job.created_at),
        "updated_at": iso(job.updated_at),
    }


# ─────────────────────────── application ────────────────────────────────────

def application_to_dict(
    app: Application,
    include_candidate: bool = False,
    include_job: bool = False,
) -> dict:
    d: dict = {
        "id": app.id,
        "job_id": app.job_id,
        "candidate_id": app.candidate_id,
        "status": app.status,
        "cover_letter": app.cover_letter,
        "resume_url": app.resume_url,
        "match_score": app.match_score,
        "confidence": app.confidence,
        "strengths": app.strengths or [],
        "gaps": app.gaps or [],
        "why_fit": app.why_fit,
        "feedback_note": app.feedback_note,
        "is_shortlisted": app.is_shortlisted,
        "created_at": iso(app.created_at),
        "updated_at": iso(app.updated_at),
    }
    if include_candidate and app.candidate:
        d["candidate"] = candidate_to_dict(app.candidate)
    if include_job and app.job:
        d["job"] = job_to_dict(app.job)
    return d


# ─────────────────────────── message ────────────────────────────────────────

def message_to_dict(msg: Message, viewer_id: int | None = None) -> dict:
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "recipient_id": msg.recipient_id,
        "application_id": msg.application_id,
        "subject": msg.subject,
        "body": msg.body,
        "is_read": msg.is_read,
        "is_mine": msg.sender_id == viewer_id if viewer_id is not None else None,
        "sender_name": msg.sender.full_name if msg.sender else None,
        "recipient_name": msg.recipient.full_name if msg.recipient else None,
        "created_at": iso(msg.created_at),
    }


# ─────────────────────────── notification ───────────────────────────────────

def notification_to_dict(notif: Notification) -> dict:
    return {
        "id": notif.id,
        "user_id": notif.user_id,
        "type": notif.type,
        "title": notif.title,
        "body": notif.body,
        "is_read": notif.is_read,
        "link": notif.link,
        "created_at": iso(notif.created_at),
    }


def audit_log_to_dict(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "user_name": log.user.full_name if log.user else "System",
        "action": log.action,
        "entity_type": log.entity_type or "system",
        "ip_address": log.ip_address or "-",
        "created_at": iso(log.created_at),
        "details": log.details or {},
    }


def bias_alert_to_dict(alert: BiasAlert) -> dict:
    return {
        "id": alert.id,
        "bias_type": alert.bias_type,
        "severity": alert.severity or "low",
        "description": alert.description or "",
        "is_resolved": bool(alert.is_resolved),
        "created_at": iso(alert.created_at),
    }


# ─────────────────────────── candidate job evaluation ───────────────────────

def evaluation_to_dict(
    ev: CandidateJobEvaluation,
    include_candidate: bool = False,
    include_job: bool = False,
) -> dict:
    d: dict = {
        "id": ev.id,
        "candidate_id": ev.candidate_id,
        "job_id": ev.job_id,
        "score": ev.score,
        "recommendation": ev.recommendation,
        "strengths": ev.strengths or [],
        "gaps": ev.gaps or [],
        "why_fit": ev.why_fit,
        "nd_inclusion": public_nd_inclusion(ev.nd_inclusion),
        "cultural_dna": ev.cultural_dna or {},
        "eval_status": ev.eval_status,
        "eval_error": ev.eval_error,
        "recruiter_action": ev.recruiter_action,
        "action_taken_at": iso(ev.action_taken_at),
        "evaluated_at": iso(ev.evaluated_at),
        "created_at": iso(ev.created_at),
        "updated_at": iso(ev.updated_at),
    }
    if include_candidate and ev.candidate:
        d["candidate"] = candidate_to_dict(ev.candidate)
    if include_job and ev.job:
        d["job"] = job_to_dict(ev.job)
    return d


# ─────────────────────────── scraped job ────────────────────────────────────

def scraped_job_to_dict(job: ScrapedJob) -> dict:
    return {
        "id": job.id,
        "region": region_to_dict(job.region) if job.region else None,
        "external_id": job.external_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": job.description,
        "tags": job.tags or [],
        "url": job.url,
        "salary": job.salary,
        "source": job.source,
        "posted_at": iso(job.posted_at),
        "scraped_at": iso(job.scraped_at),
    }


# ─────────────────────────── feedback report ────────────────────────────────

def feedback_report_to_dict(report) -> dict:
    """Serialize FeedbackReport model."""
    if report is None:
        return {}
    return {
        "id": report.id,
        "evaluation_id": report.evaluation_id,
        "candidate_report": report.candidate_report,
        "recruiter_summary": report.recruiter_summary,
        "interview_questions": report.interview_questions or [],
        "fairness_assessment": report.fairness_assessment,
        "learning_resources": report.learning_resources or {},
        "task_checklist": report.task_checklist or [],
        "generated_at": iso(report.generated_at),
        "generation_time_ms": report.generation_time_ms,
    }
