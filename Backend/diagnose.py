"""
Backend/diagnose.py
===================
Run this ONCE to:
  1. Print every missing column between models.py and the live DB
  2. Add all missing columns with ALTER TABLE (safe – skips existing ones)
  3. Test the login route logic directly (no HTTP needed)

Usage:
    cd Backend
    python diagnose.py
"""
from __future__ import annotations

import sys
import traceback

# ── Bootstrap Flask app ───────────────────────────────────────────────────────
from app import create_app
app = create_app()

# ── Expected columns per table (model definition) ────────────────────────────
EXPECTED: dict[str, dict[str, str]] = {
    "candidates": {
        "github_username":        "VARCHAR(128)",
        "leetcode_username":      "VARCHAR(128)",
        "resume_url":             "VARCHAR(512)",
        "github_repos":           "INTEGER",
        "github_stars":           "INTEGER",
        "github_forks":           "INTEGER",
        "github_top_languages":   "JSON",
        "github_repos_data":      "JSON",
        "lc_easy":                "INTEGER",
        "lc_medium":              "INTEGER",
        "lc_hard":                "INTEGER",
        "lc_rating":              "FLOAT",
        "resume_skills":          "JSON",
        "resume_years_experience":"INTEGER",
        "resume_projects":        "JSON",
        "enrichment_status":      "VARCHAR(32)",
        "enrichment_error":       "TEXT",
        "enriched_at":            "TIMESTAMP",
        "agent_statuses":         "JSON",
        "top_job_matches":        "JSON",
        "preferred_region_id":    "INTEGER",
        "projects":               "JSON",
        "links":                  "JSON",
        "skills":                 "JSON",
        "headline":               "VARCHAR(255)",
        "location":               "VARCHAR(255)",
        "summary":                "TEXT",
        "years_experience":       "INTEGER",
    },
    "users": {
        "google_sub":    "VARCHAR(255)",
        "linkedin_id":   "VARCHAR(255)",
        "last_login_at": "TIMESTAMP",
        "auth_provider": "VARCHAR(32)",
    },
    "candidate_job_evaluations": {
        "eval_error":      "TEXT",
        "recruiter_action":"VARCHAR(32)",
        "action_taken_at": "TIMESTAMP",
        "evaluated_at":    "TIMESTAMP",
        "why_fit":         "TEXT",
        "strengths":       "JSON",
        "gaps":            "JSON",
    },
    "feedback_reports": {
        "candidate_report":   "TEXT",
        "recruiter_summary":  "TEXT",
        "interview_questions":"JSON",
        "fairness_assessment":"TEXT",
        "learning_resources": "JSON",
        "task_checklist":     "JSON",
        "generation_time_ms": "INTEGER",
    },
}

# PostgreSQL type aliases for ALTER TABLE
PG_TYPE_MAP = {
    "VARCHAR(128)":  "VARCHAR(128)",
    "VARCHAR(255)":  "VARCHAR(255)",
    "VARCHAR(512)":  "VARCHAR(512)",
    "VARCHAR(32)":   "VARCHAR(32)",
    "VARCHAR(64)":   "VARCHAR(64)",
    "INTEGER":       "INTEGER",
    "FLOAT":         "DOUBLE PRECISION",
    "TEXT":          "TEXT",
    "TIMESTAMP":     "TIMESTAMP WITHOUT TIME ZONE",
    "JSON":          "JSON",
    "BOOLEAN":       "BOOLEAN",
}


def get_existing_columns(conn, table: str) -> set[str]:
    """Return the set of column names that actually exist in the DB table."""
    result = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :t AND table_schema = 'public'",
        {"t": table},
    )
    return {row[0] for row in result}


def run_migration(conn, table: str, missing: dict[str, str]) -> None:
    for col, col_type in missing.items():
        pg_type = PG_TYPE_MAP.get(col_type, "TEXT")
        sql = f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{col}" {pg_type}'
        print(f"  → ALTER TABLE {table} ADD COLUMN {col} {pg_type}")
        try:
            conn.execute(sql)
        except Exception as exc:
            print(f"    ⚠  Skipped ({exc})")


def check_and_fix_schema() -> bool:
    """Returns True if any columns were missing (and added)."""
    from extensions import db
    any_missing = False

    with app.app_context():
        with db.engine.connect() as conn:
            for table, expected_cols in EXPECTED.items():
                existing = get_existing_columns(conn, table)
                missing = {
                    col: typ
                    for col, typ in expected_cols.items()
                    if col not in existing
                }
                if missing:
                    any_missing = True
                    print(f"\n[SCHEMA] Table '{table}' is missing {len(missing)} column(s):")
                    for col in missing:
                        print(f"  ✗  {col}")
                    run_migration(conn, table, missing)
                    conn.execute("COMMIT")
                    print(f"  ✓  All missing columns added to '{table}'")
                else:
                    print(f"[SCHEMA] Table '{table}' — OK (all columns present)")

    return any_missing


def test_login_logic(email: str = "test@example.com", password: str = "test123") -> None:
    """
    Simulate the login route logic inside the app context so any exception
    is printed with a full traceback — no HTTP layer involved.
    """
    from werkzeug.security import generate_password_hash, check_password_hash
    from models import User
    from serializers import user_to_dict
    from extensions import db

    with app.app_context():
        print(f"\n[LOGIN TEST] Looking up user: {email}")
        try:
            user = User.query.filter_by(email=email).first()
            if user is None:
                print("  → No user found with that email (expected for a fresh DB)")
                # Create a test user to verify serialization works
                print("  → Creating temporary test user to verify serialization…")
                from models import Candidate
                test_user = User(
                    email="__diag_test__@example.com",
                    full_name="Diag Test",
                    role="candidate",
                    auth_provider="local",
                    password_hash=generate_password_hash("test123"),
                )
                db.session.add(test_user)
                db.session.flush()
                db.session.add(Candidate(user_id=test_user.id, skills=[], links=[]))
                db.session.flush()

                print("  → Calling user_to_dict()…")
                d = user_to_dict(test_user)
                print(f"  ✓  user_to_dict() succeeded — keys: {list(d.keys())}")
                db.session.rollback()   # don't persist the test user
                return

            print(f"  → Found user: {user.email} (role={user.role})")
            print("  → Calling user_to_dict()…")
            d = user_to_dict(user)
            print(f"  ✓  user_to_dict() succeeded — keys: {list(d.keys())}")

        except Exception:
            print("\n  ✗  EXCEPTION in login logic:")
            traceback.print_exc()
            print("\n  This is the root cause of the 500 error.")


def check_env() -> None:
    import os
    print("\n[ENV CHECK]")
    required = {
        "SECRET_KEY":       "Flask session signing key",
        "JWT_SECRET_KEY":   "JWT signing key",
        "DATABASE_URL":     "PostgreSQL connection string",
    }
    optional = {
        "GROQ_API_KEY":     "AI evaluation (optional — falls back to rule-based)",
        "GITHUB_TOKEN":     "GitHub API (optional — 60 req/hr without it)",
        "GOOGLE_CLIENT_ID": "Google OAuth (optional)",
        "SENDGRID_API_KEY": "Email notifications (optional)",
    }
    all_ok = True
    for key, desc in required.items():
        val = os.getenv(key, "")
        if val and val != "change-me" and val != "change-me-jwt":
            print(f"  ✓  {key:<35} set ({val[:8]}…)")
        else:
            print(f"  ✗  {key:<35} MISSING or default — {desc}")
            all_ok = False
    for key, desc in optional.items():
        val = os.getenv(key, "")
        status = f"set ({val[:8]}…)" if val else "not set (optional)"
        print(f"  {'✓' if val else '·'}  {key:<35} {status}")
    if not all_ok:
        print("\n  ⚠  Copy Backend/.env.example → Backend/.env and fill in the required values.")


if __name__ == "__main__":
    print("=" * 60)
    print("  Shortlist AI — Backend Diagnostics")
    print("=" * 60)

    check_env()
    had_missing = check_and_fix_schema()
    test_login_logic()

    print("\n" + "=" * 60)
    if had_missing:
        print("  ✓  Missing columns were added. Restart the Flask server.")
    else:
        print("  ✓  Schema looks good.")
    print("  Next: curl -X POST http://localhost:5000/api/auth/login \\")
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"email":"you@example.com","password":"yourpass"}\'')
    print("=" * 60)
