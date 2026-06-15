from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
from core.database import get_db
from models import User, AuditLog, BiasAlert, CandidateJobEvaluation, Job, FeedbackReport
from auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin"])

def require_superadmin(current_user = Depends(get_current_user)):
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ... rest of your endpoints ...

# ... rest of the file unchanged ...


# ──────────────────────────────────────────────────────────────────────────────
# Inclusion Settings Models
# ──────────────────────────────────────────────────────────────────────────────

class InclusionSettings(BaseModel):
    enabled: bool = True
    nd_detection_sensitivity: str = "medium"  # low, medium, high
    detect_hyperfocus: bool = True
    detect_pattern_recognition: bool = True
    detect_debugging_consistency: bool = True
    apply_score_uplift: bool = True
    generate_accessible_summaries: bool = True
    flag_underestimation_risks: bool = True
    output_format: str = "standard"  # standard, adhd_friendly, dyslexia_friendly


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard Stats
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_admin_stats(
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for super admin"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    return {
        "total_users": db.query(User).count(),
        "total_candidates": db.query(User).filter(User.role == "candidate").count(),
        "total_recruiters": db.query(User).filter(User.role == "recruiter").count(),
        "total_evaluations": db.query(CandidateJobEvaluation).count(),
        "flagged_hirings": db.query(CandidateJobEvaluation)
            .filter(CandidateJobEvaluation.recruiter_action == "rejected")
            .filter(CandidateJobEvaluation.score < 40).count(),
        "active_reports": db.query(CandidateJobEvaluation)
            .filter(CandidateJobEvaluation.eval_status == "running").count(),
        "security_events_7d": db.query(AuditLog)
            .filter(AuditLog.created_at >= week_ago).count(),
        "bias_alerts": db.query(BiasAlert)
            .filter(BiasAlert.is_resolved == False).count(),
        "avg_evaluation_score": db.query(func.avg(CandidateJobEvaluation.score)).scalar() or 0,
        "shortlist_rate": (
            db.query(CandidateJobEvaluation)
            .filter(CandidateJobEvaluation.recruiter_action == "shortlisted").count() / 
            max(db.query(CandidateJobEvaluation).count(), 1) * 100
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# User Management
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/users")
async def get_all_users(
    admin = Depends(require_superadmin),
    role: Optional[str] = Query(None),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all users with filtering"""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    
    total = query.count()
    users = query.offset(offset).limit(limit).all()
    
    return {"total": total, "users": users}


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    data: dict,
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Activate or deactivate a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = data.get("is_active", user.is_active)
    db.commit()
    
    return {"success": True, "is_active": user.is_active}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Delete a user (super admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"success": True, "message": f"User {user.email} deleted"}


# ──────────────────────────────────────────────────────────────────────────────
# Audit Logs
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    admin = Depends(require_superadmin),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    days: int = 30,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get audit trail logs - fetches all records without time filters for live display"""
    # Fetch ALL logs (no time filter) to show real-time activity
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    # Add user names to logs
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "user_name": user.full_name if user else "Unknown",
            "action": log.action,
            "entity_type": log.entity_type,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
            "details": log.details,
        })
    
    return {"logs": result}


# ──────────────────────────────────────────────────────────────────────────────
# Bias Alerts
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/bias-alerts")
async def get_bias_alerts(
    admin = Depends(require_superadmin),
    resolved: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """Get bias detection alerts"""
    query = db.query(BiasAlert)
    if resolved is not None:
        query = query.filter(BiasAlert.is_resolved == resolved)
    
    alerts = query.order_by(BiasAlert.created_at.desc()).all()
    
    return {"alerts": alerts}


@router.patch("/bias-alerts/{alert_id}/resolve")
async def resolve_bias_alert(
    alert_id: int,
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Mark a bias alert as resolved"""
    alert = db.query(BiasAlert).filter(BiasAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_resolved = True
    db.commit()
    
    return {"success": True, "message": "Alert resolved"}


@router.post("/bias-alerts/generate-test")
async def generate_test_bias_alerts(
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Generate test bias alerts for demo/testing purposes"""
    test_alerts = [
        {
            "bias_type": "gender_imbalance",
            "severity": "high",
            "description": "Evaluation history shows 23% higher rejection rate for female candidates in similar roles. Manual review recommended."
        },
        {
            "bias_type": "educational_bias",
            "severity": "medium",
            "description": "Non-traditional education paths (bootcamps, self-taught) are underrepresented in shortlist. Consider inclusion scoring."
        },
        {
            "bias_type": "geographic_bias",
            "severity": "medium",
            "description": "Candidates from tier-2 cities have lower match scores despite similar skill profiles. Review location weighting."
        },
    ]
    
    created_alerts = []
    for alert_data in test_alerts:
        existing = db.query(BiasAlert).filter(
            BiasAlert.bias_type == alert_data["bias_type"],
            BiasAlert.is_resolved == False
        ).first()
        
        if not existing:
            alert = BiasAlert(
                bias_type=alert_data["bias_type"],
                severity=alert_data["severity"],
                description=alert_data["description"],
                is_resolved=False
            )
            db.add(alert)
            created_alerts.append(alert_data)
    
    db.commit()
    return {
        "success": True,
        "message": f"Created {len(created_alerts)} test bias alerts",
        "created": created_alerts
    }


@router.get("/reports")
async def get_admin_reports(
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get all evaluation reports with fairness assessments"""
    reports = db.query(FeedbackReport).join(
        CandidateJobEvaluation,
        FeedbackReport.evaluation_id == CandidateJobEvaluation.id
    ).all()
    
    result = []
    for report in reports:
        eval_obj = report.evaluation
        
        # Determine risk level based on fairness assessment
        fairness_text = (report.fairness_assessment or "").lower()
        if any(keyword in fairness_text for keyword in ["high risk", "critical", "severe bias"]):
            risk_level = "high"
        elif any(keyword in fairness_text for keyword in ["medium risk", "moderate", "review recommended"]):
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Extract candidate and job info
        candidate_name = "Unknown"
        job_title = "Unknown"
        company = "Unknown"
        
        if eval_obj.candidate and eval_obj.candidate.user:
            candidate_name = eval_obj.candidate.user.full_name
        
        if eval_obj.job:
            job_title = eval_obj.job.title or "Unknown"
            company = eval_obj.job.company or "Unknown"
        
        result.append({
            "id": report.id,
            "evaluation_id": report.evaluation_id,
            "candidate_name": candidate_name,
            "job_title": job_title,
            "company": company,
            "score": eval_obj.score,
            "recommendation": eval_obj.recommendation,
            "fairness_assessment": report.fairness_assessment,
            "recruiter_summary": report.recruiter_summary,
            "interview_questions": report.interview_questions,
            "risk_level": risk_level,
            "generated_at": report.generated_at,
            "generation_time_ms": report.generation_time_ms
        })
    
    return {"reports": result}


# ──────────────────────────────────────────────────────────────────────────────
# Inclusion Agent Settings
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/inclusion-settings")
async def get_job_inclusion_settings(
    job_id: int,
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get inclusion settings for a specific job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    settings = job.inclusion_settings or {}
    # Merge with defaults
    default_settings = InclusionSettings().dict()
    merged = {**default_settings, **settings}
    
    return merged


@router.patch("/jobs/{job_id}/inclusion-settings")
async def update_job_inclusion_settings(
    job_id: int,
    settings: InclusionSettings,
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Update inclusion settings for a specific job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    current = job.inclusion_settings or {}
    current.update(settings.dict(exclude_unset=True))
    job.inclusion_settings = current
    db.commit()
    
    return current


@router.get("/inclusion/status")
async def get_global_inclusion_status(
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get global inclusion agent status"""
    # You can store this in a settings table or config
    # For now, return default enabled
    return {"enabled": True}


@router.post("/inclusion/toggle")
async def toggle_inclusion_agent(
    data: dict,
    admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Toggle global inclusion agent on/off"""
    enabled = data.get("enabled", False)
    # Store in settings table (you'll need to create one)
    # For now, just return success
    return {"enabled": enabled}