from __future__ import annotations

from datetime import datetime

from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="candidate")
    auth_provider = db.Column(db.String(32), nullable=False, default="local")
    google_sub = db.Column(db.String(255), unique=True)
    linkedin_id = db.Column(db.String(255), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime)

    candidate = db.relationship("Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recruiter = db.relationship("Recruiter", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    headline = db.Column(db.String(255))
    location = db.Column(db.String(255))
    summary = db.Column(db.Text)
    years_experience = db.Column(db.Integer)
    skills = db.Column(db.JSON, nullable=False, default=list)
    links = db.Column(db.JSON, nullable=False, default=list)
    projects = db.Column(db.JSON, nullable=False, default=list)  # [{name, description, url}] manually entered
    neurodivergent = db.Column(db.Boolean, nullable=True, default=None)
    nd_type = db.Column(db.String(50), nullable=True)
    # ── enrichment fields ────────────────────────────────────────────────────
    github_username = db.Column(db.String(128))
    leetcode_username = db.Column(db.String(128))
    resume_url = db.Column(db.String(512))
# GitHub agent results
    github_repos = db.Column(db.Integer)
    github_stars = db.Column(db.Integer)
    github_forks = db.Column(db.Integer)
    github_top_languages = db.Column(db.JSON, default=list)
    github_repos_data = db.Column(db.JSON, default=list)   # full repo list [{name, stars, forks, language, url, description}]
    # LeetCode agent results
    lc_easy = db.Column(db.Integer)
    lc_medium = db.Column(db.Integer)
    lc_hard = db.Column(db.Integer)
    lc_rating = db.Column(db.Float)
    # Resume parser results
    resume_skills = db.Column(db.JSON, default=list)
    resume_years_experience = db.Column(db.Integer)
    resume_projects = db.Column(db.JSON, default=list)   # [{name, description}] extracted from resume
    # Enrichment status: "pending" | "running" | "done" | "error"
    enrichment_status = db.Column(db.String(32), default="none")
    enrichment_error = db.Column(db.Text)
    enriched_at = db.Column(db.DateTime)
    # Per-agent statuses: {"github": "done", "leetcode": "skipped", ...}
    agent_statuses = db.Column(db.JSON, default=dict)
    # Top 3 job matches from job_match agent
    top_job_matches = db.Column(db.JSON, default=list)
    # Preferred region for job recommendations
    preferred_region_id = db.Column(db.Integer, db.ForeignKey("regions.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="candidate")
    preferred_region = db.relationship("Region", foreign_keys=[preferred_region_id])
    applications = db.relationship("Application", back_populates="candidate", cascade="all, delete-orphan")


class Recruiter(db.Model):
    __tablename__ = "recruiters"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_name = db.Column(db.String(255))
    job_title = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="recruiter")
    jobs = db.relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------

class Region(db.Model):
    __tablename__ = "regions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)  # e.g., "India", "USA", "Remote"
    code = db.Column(db.String(16), unique=True, nullable=False)   # e.g., "IN", "US", "REMOTE"
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    jobs = db.relationship("Job", back_populates="region")
    scraped_jobs = db.relationship("ScrapedJob", back_populates="region")


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False, index=True)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id", ondelete="SET NULL"), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    employment_type = db.Column(db.String(64), default="Full-time")   # Full-time / Part-time / Contract
    description = db.Column(db.Text)
    requirements = db.Column(db.JSON, nullable=False, default=list)   # list of strings
    skills_required = db.Column(db.JSON, nullable=False, default=list)
    inclusion_settings = db.Column(db.JSON, nullable=False, default=dict)
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    recruiter = db.relationship("Recruiter", back_populates="jobs")
    region = db.relationship("Region", back_populates="jobs")
    applications = db.relationship("Application", back_populates="job", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

APPLICATION_STATUSES = ("applied", "in_review", "shortlisted", "rejected", "on_hold")


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="applied")
    cover_letter = db.Column(db.Text)
    resume_url = db.Column(db.String(512))
    match_score = db.Column(db.Integer)          # 0-100, set by AI pipeline
    confidence = db.Column(db.String(16))        # High / Medium / Low
    strengths = db.Column(db.JSON, default=list)
    gaps = db.Column(db.JSON, default=list)
    why_fit = db.Column(db.Text)
    feedback_note = db.Column(db.Text)
    is_shortlisted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    job = db.relationship("Job", back_populates="applications")
    candidate = db.relationship("Candidate", back_populates="applications")

    __table_args__ = (
        db.UniqueConstraint("job_id", "candidate_id", name="uq_application_job_candidate"),
    )


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True)
    subject = db.Column(db.String(255), default="New Message")
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

NOTIFICATION_TYPES = ("application_received", "status_changed", "shortlisted", "message_received", "general")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(64), nullable=False, default="general")
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    link = db.Column(db.String(512))             # frontend route to navigate to
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])


# ---------------------------------------------------------------------------
# CandidateJobEvaluation  – AI evaluation result per candidate+job pair
# ---------------------------------------------------------------------------

EVALUATION_RECOMMENDATIONS = ("YES", "NO", "PENDING")
RECRUITER_ACTIONS = ("pending", "shortlisted", "rejected")


class CandidateJobEvaluation(db.Model):
    __tablename__ = "candidate_job_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    # AI pipeline outputs
    score = db.Column(db.Float)                          # 0-100
    recommendation = db.Column(db.String(16), default="PENDING")  # YES / NO / PENDING
    strengths = db.Column(db.JSON, default=list)
    gaps = db.Column(db.JSON, default=list)
    why_fit = db.Column(db.Text)
    nd_inclusion = db.Column(db.JSON, default=dict)
    cultural_dna = db.Column(db.JSON, default=dict)
    eval_status = db.Column(db.String(32), default="pending")  # pending / running / done / error
    eval_error = db.Column(db.Text)
    # Recruiter human-in-the-loop decision
    recruiter_action = db.Column(db.String(32), default="pending")  # pending / shortlisted / rejected
    action_taken_at = db.Column(db.DateTime)
    evaluated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    candidate = db.relationship("Candidate", backref=db.backref("job_evaluations", cascade="all, delete-orphan"))
    job = db.relationship("Job", backref=db.backref("evaluations", cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint("candidate_id", "job_id", name="uq_eval_candidate_job"),
    )


# ---------------------------------------------------------------------------
# ScrapedJob  – live jobs pulled from RemoteOK (or similar public APIs)
# ---------------------------------------------------------------------------

class ScrapedJob(db.Model):
    __tablename__ = "scraped_jobs"

    id = db.Column(db.Integer, primary_key=True)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id", ondelete="SET NULL"), nullable=True)
    external_id = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), default="Remote")
    description = db.Column(db.Text)
    tags = db.Column(db.JSON, nullable=False, default=list)   # required skills / tags
    url = db.Column(db.String(512))
    salary = db.Column(db.String(128))
    source = db.Column(db.String(64), default="remoteok")
    posted_at = db.Column(db.DateTime)  # when the job was posted
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    region = db.relationship("Region", back_populates="scraped_jobs")

    __table_args__ = (
        db.UniqueConstraint("url", "posted_at", name="uq_scraped_job_url_posted"),
    )


# ---------------------------------------------------------------------------
# RawJobFeed  – raw scraped data before deduplication
# ---------------------------------------------------------------------------

class RawJobFeed(db.Model):
    __tablename__ = "raw_job_feeds"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(64), nullable=False)          # remoteok | hn | stackoverflow | indeed
    external_id = db.Column(db.String(255), nullable=False)
    raw_data = db.Column(db.JSON, nullable=False, default=dict)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("source", "external_id", name="uq_raw_feed_source_ext"),
    )


# ---------------------------------------------------------------------------
# JobAlert  – tracks which candidates have been alerted for which scraped jobs
# ---------------------------------------------------------------------------

class JobAlert(db.Model):
    __tablename__ = "job_alerts"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    scraped_job_id = db.Column(db.Integer, db.ForeignKey("scraped_jobs.id", ondelete="CASCADE"), nullable=False)
    match_score = db.Column(db.Integer, default=0)
    alerted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    email_sent = db.Column(db.Boolean, default=False, nullable=False)

    candidate = db.relationship("Candidate", backref=db.backref("job_alerts", cascade="all, delete-orphan"))
    scraped_job = db.relationship("ScrapedJob", backref=db.backref("alerts", cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint("candidate_id", "scraped_job_id", name="uq_job_alert_candidate_job"),
    )


# ---------------------------------------------------------------------------
# AlertSubscription  – candidate opt-in for real-time job alerts
# ---------------------------------------------------------------------------

class AlertSubscription(db.Model):
    __tablename__ = "alert_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    min_match_score = db.Column(db.Integer, default=30)   # only alert if match >= this
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    candidate = db.relationship("Candidate", backref=db.backref("alert_subscription", uselist=False, cascade="all, delete-orphan"))


# ---------------------------------------------------------------------------
# FeedbackReport – AI-generated reports for candidate and recruiter
# ---------------------------------------------------------------------------

class FeedbackReport(db.Model):
    __tablename__ = "feedback_reports"

    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(
        db.Integer,
        db.ForeignKey("candidate_job_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Candidate-facing report (markdown)
    candidate_report = db.Column(db.Text)
    # Recruiter-facing summary (markdown)
    recruiter_summary = db.Column(db.Text)
    # Suggested interview questions (JSON array of strings)
    interview_questions = db.Column(db.JSON, default=list)
    # Fairness/bias assessment
    fairness_assessment = db.Column(db.Text)
    # Learning resources (JSON: {weekly_plan: [...], resources: [...], trends: [...]})
    learning_resources = db.Column(db.JSON, default=dict)
    # Task checklist (JSON: [{id, task, completed, week, resource_url, type}])
    task_checklist = db.Column(db.JSON, default=list)
    # Generation metadata
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    generation_time_ms = db.Column(db.Integer)  # Time taken to generate report

    evaluation = db.relationship(
        "CandidateJobEvaluation",
        backref=db.backref("feedback_report", uselist=False, cascade="all, delete-orphan"),
    )


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(255), nullable=False)
    entity_type = db.Column(db.String(128))
    ip_address = db.Column(db.String(64))
    details = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])


# ---------------------------------------------------------------------------
# BiasAlert
# ---------------------------------------------------------------------------

class BiasAlert(db.Model):
    __tablename__ = "bias_alerts"

    id = db.Column(db.Integer, primary_key=True)
    bias_type = db.Column(db.String(128), nullable=False)  # e.g., 'gender_imbalance', 'geographic_bias'
    severity = db.Column(db.String(16), default='low')
    description = db.Column(db.Text)
    is_resolved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# CandidateInterview – voice interview sessions
# ---------------------------------------------------------------------------

class CandidateInterview(db.Model):
    __tablename__ = "candidate_interviews"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluation_id = db.Column(
        db.Integer,
        db.ForeignKey("candidate_job_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(20), nullable=False, default="started")  # started | completed
    # Full transcript: [{id, question, focus_area, answer, assessment:{score,sentiment,key_point}}]
    transcript = db.Column(db.JSON, nullable=False, default=list)
    overall_score = db.Column(db.Float)          # average of per-question scores (1-10)
    duration_seconds = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    candidate = db.relationship(
        "Candidate",
        backref=db.backref("interviews", cascade="all, delete-orphan"),
    )
    evaluation = db.relationship(
        "CandidateJobEvaluation",
        backref=db.backref("interviews", cascade="all, delete-orphan"),
    )


# ---------------------------------------------------------------------------
# LiveKitInterview  – voice interview sessions via LiveKit agent (Priya)
# ---------------------------------------------------------------------------

class LiveKitInterview(db.Model):
    __tablename__ = "livekit_interviews"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evaluation_id = db.Column(
        db.Integer,
        db.ForeignKey("candidate_job_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    livekit_room = db.Column(db.String(200), nullable=True, index=True)
    phone_number = db.Column(db.String(30), nullable=True)
    trade = db.Column(db.String(100), nullable=True)
    language = db.Column(db.String(50), default="English")
    scores = db.Column(db.JSON, default=list)           # list of ints (0-10 per question)
    avg_score = db.Column(db.Float, nullable=True)
    fitment = db.Column(db.String(60), nullable=True)   # Job-Ready | Requires Training | etc.
    weak_topics = db.Column(db.JSON, default=list)
    feedback = db.Column(db.JSON, nullable=True)        # {strengths: [], improvements: []}
    transcript = db.Column(db.JSON, default=list)       # messages list from agent
    status = db.Column(db.String(20), default="started")  # started | completed | partial
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    candidate = db.relationship(
        "Candidate",
        backref=db.backref("livekit_interviews", cascade="all, delete-orphan"),
    )
    evaluation = db.relationship(
        "CandidateJobEvaluation",
        backref=db.backref("livekit_interview", uselist=False),
    )
