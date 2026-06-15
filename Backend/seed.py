"""
Seed the database with demo data.

Run from the Backend/ directory:
    python seed.py

Creates:
  - 1 recruiter  : john@shortlistai.com  / password: recruiter123
  - 3 candidates : jr@example.com        / password: candidate123
                   sarah@example.com     / password: candidate123
                   david@example.com     / password: candidate123
  - 1 job        : Senior Full Stack Developer
  - 3 applications (one per candidate, with AI-style scores)
  - 2 messages   (recruiter → JR, JR → recruiter)
  - 3 notifications for JR
"""

from __future__ import annotations

from app import create_app
from extensions import db
from models import (
    Application, Candidate, Job, Message, Notification, Recruiter, Region, ScrapedJob, User,
)
from werkzeug.security import generate_password_hash


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # ── wipe existing seed users so re-running is safe ──────────────────
        for email in (
            "john@shortlistai.com",
            "jr@example.com",
            "sarah@example.com",
            "david@example.com",
        ):
            u = User.query.filter_by(email=email).first()
            if u:
                db.session.delete(u)
        db.session.commit()

        # ── recruiter ────────────────────────────────────────────────────────
        recruiter_user = User(
            email="john@shortlistai.com",
            full_name="John Recruiter",
            role="recruiter",
            auth_provider="local",
            password_hash=generate_password_hash("recruiter123"),
        )
        db.session.add(recruiter_user)
        db.session.flush()

        recruiter_profile = Recruiter(
            user_id=recruiter_user.id,
            company_name="ShortlistAI",
            job_title="Senior Recruiter",
        )
        db.session.add(recruiter_profile)
        db.session.flush()

        # ── regions ──────────────────────────────────────────────────────────
        regions_data = [
            {"name": "India", "code": "IN"},
            {"name": "USA", "code": "US"},
            {"name": "Remote", "code": "REMOTE"},
            {"name": "Germany", "code": "DE"},
            {"name": "UK", "code": "GB"},
        ]
        regions = {}
        for r_data in regions_data:
            region = Region(
                name=r_data["name"],
                code=r_data["code"],
                is_active=True,
            )
            db.session.add(region)
            regions[r_data["code"]] = region
        db.session.flush()

        # ── job ──────────────────────────────────────────────────────────────
        job = Job(
            recruiter_id=recruiter_profile.id,
            region_id=regions["REMOTE"].id,
            title="Senior Full Stack Developer",
            company="ShortlistAI",
            location="Berlin, Hybrid",
            employment_type="Full-time",
            description=(
                "We are looking for a Senior Full Stack Developer to join our growing team. "
                "You will work on our AI-powered hiring platform, building features that help "
                "recruiters make fairer, faster decisions."
            ),
            requirements=[
                "5+ years of professional software development experience",
                "Strong proficiency in React and TypeScript",
                "Experience with Node.js or Python backends",
                "Familiarity with PostgreSQL or similar relational databases",
                "Experience with cloud platforms (AWS, GCP, or Azure)",
            ],
            skills_required=["React", "TypeScript", "Node.js", "PostgreSQL", "AWS"],
            salary_min=90000,
            salary_max=130000,
            is_active=True,
        )
        db.session.add(job)
        db.session.flush()

        # ── candidates ───────────────────────────────────────────────────────
        jr_user = User(
            email="jr@example.com",
            full_name="Jordan Rivera",
            role="candidate",
            auth_provider="local",
            password_hash=generate_password_hash("candidate123"),
        )
        sarah_user = User(
            email="sarah@example.com",
            full_name="Sarah Mitchell",
            role="candidate",
            auth_provider="local",
            password_hash=generate_password_hash("candidate123"),
        )
        david_user = User(
            email="david@example.com",
            full_name="David Park",
            role="candidate",
            auth_provider="local",
            password_hash=generate_password_hash("candidate123"),
        )
        db.session.add_all([jr_user, sarah_user, david_user])
        db.session.flush()

        jr_profile = Candidate(
            user_id=jr_user.id,
            headline="Senior Frontend Engineer",
            location="London, UK",
            summary="5 years building React applications with a focus on accessibility and design systems.",
            years_experience=5,
            skills=["React 18", "TypeScript", "Design Systems", "Accessibility (WCAG 2.2)", "Node.js"],
            links=["https://github.com/jordanrivera", "https://leetcode.com/jordanrivera"],
        )
        sarah_profile = Candidate(
            user_id=sarah_user.id,
            headline="Senior Full Stack Engineer",
            location="Berlin, Germany",
            summary="Full stack engineer with 7 years of experience building production systems at scale.",
            years_experience=7,
            skills=["React 18", "TypeScript", "Node.js", "PostgreSQL", "System Design"],
            links=["https://github.com/sarahmitchell"],
        )
        david_profile = Candidate(
            user_id=david_user.id,
            headline="Full Stack Engineer",
            location="Seoul, South Korea",
            summary="Backend-leaning full stack engineer with strong ML Ops experience.",
            years_experience=4,
            skills=["Python", "FastAPI", "AWS", "ML Ops", "React"],
            links=["https://github.com/davidpark"],
        )
        db.session.add_all([jr_profile, sarah_profile, david_profile])
        db.session.flush()

        # ── applications ─────────────────────────────────────────────────────
        app_jr = Application(
            job_id=job.id,
            candidate_id=jr_profile.id,
            status="in_review",
            cover_letter="I am excited to apply for this role. My React and accessibility expertise aligns well.",
            match_score=88,
            confidence="High",
            strengths=["React 18", "TypeScript", "Accessibility", "Design Systems"],
            gaps=["PostgreSQL (intermediate)", "AWS (basic)"],
            why_fit="Strong frontend depth with growing backend skills. Accessibility expertise is a differentiator.",
            feedback_note="Recommend a take-home task focused on full-stack feature implementation.",
            is_shortlisted=False,
        )
        app_sarah = Application(
            job_id=job.id,
            candidate_id=sarah_profile.id,
            status="shortlisted",
            cover_letter="7 years of full stack experience, including production systems at 10M+ req/day.",
            match_score=94,
            confidence="High",
            strengths=["React 18", "TypeScript", "Node.js", "PostgreSQL", "System Design"],
            gaps=["Kubernetes (basic)", "GraphQL (intermediate)"],
            why_fit="Exceptional full stack depth. 14 production React/TS apps. Strong ownership of backend stacks.",
            feedback_note="Advance to onsite. Probe GraphQL depth and K8s exposure.",
            is_shortlisted=True,
        )
        app_david = Application(
            job_id=job.id,
            candidate_id=david_profile.id,
            status="in_review",
            cover_letter="Strong backend and ML Ops background, rapidly growing React skills.",
            match_score=82,
            confidence="Medium",
            strengths=["Python", "FastAPI", "AWS", "ML Ops"],
            gaps=["React (intermediate)", "TypeScript (basic)"],
            why_fit="Strong backend depth with ML ops experience. Frontend skills trending up.",
            feedback_note="Suggest pair-programming task to assess React fluency.",
            is_shortlisted=False,
        )
        db.session.add_all([app_jr, app_sarah, app_david])
        db.session.flush()

        # ── messages ─────────────────────────────────────────────────────────
        msg1 = Message(
            sender_id=recruiter_user.id,
            recipient_id=jr_user.id,
            application_id=app_jr.id,
            body=(
                "Hi Jordan, thanks for applying to the Senior Full Stack Developer role at ShortlistAI. "
                "We've reviewed your profile and would love to schedule a 30-minute intro call. "
                "Are you available this week?"
            ),
            is_read=False,
        )
        msg2 = Message(
            sender_id=jr_user.id,
            recipient_id=recruiter_user.id,
            application_id=app_jr.id,
            body="Hi John, thanks for reaching out! I'm available Thursday or Friday afternoon. Looking forward to it.",
            is_read=True,
        )
        db.session.add_all([msg1, msg2])
        db.session.flush()

        # ── notifications for JR ─────────────────────────────────────────────
        notif1 = Notification(
            user_id=jr_user.id,
            type="message_received",
            title="New message from John Recruiter",
            body="Hi Jordan, thanks for applying to the Senior Full Stack Developer role…",
            is_read=False,
            link="/candidate/messages",
        )
        notif2 = Notification(
            user_id=jr_user.id,
            type="status_changed",
            title="Application update: Senior Full Stack Developer",
            body="Your application status changed to In Review",
            is_read=False,
            link="/candidate/applications",
        )
        notif3 = Notification(
            user_id=jr_user.id,
            type="general",
            title="Complete your profile to boost your match score",
            body="Add your GitHub link and years of experience to improve AI matching.",
            is_read=True,
            link="/candidate/profile",
        )
        db.session.add_all([notif1, notif2, notif3])

        # ── notification for recruiter ────────────────────────────────────────
        notif_r = Notification(
            user_id=recruiter_user.id,
            type="application_received",
            title="New application: Jordan Rivera",
            body="Jordan Rivera applied for Senior Full Stack Developer",
            is_read=False,
            link="/dashboard/projects",
        )
        db.session.add(notif_r)

        db.session.commit()
        print("✅ Seed complete.")
        print("   Recruiter : john@shortlistai.com  / recruiter123")
        print("   Candidate : jr@example.com        / candidate123")
        print("   Candidate : sarah@example.com     / candidate123")
        print("   Candidate : david@example.com     / candidate123")


if __name__ == "__main__":
    seed()
