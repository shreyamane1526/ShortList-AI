"""
migrate.py – idempotent schema migration script.

Creates all tables that don't exist yet and adds any missing columns to
existing tables. Safe to run multiple times.

Usage:
    python migrate.py

The script reads DATABASE_URL from Backend/.env (same as the app).
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _column_exists(conn, table: str, column: str) -> bool:
    """Check whether a column exists in a table."""
    try:
        if is_pg:
            # Use information_schema for PostgreSQL
            result = conn.execute(
                "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
                (table, column)
            )
            return result.fetchone() is not None
        else:
            # SQLite approach
            result = conn.execute(
                f"SELECT {column} FROM {table} LIMIT 0"  # noqa: S608
            )
            result.close()
            return True
    except Exception:
        return False


def _table_exists(conn, table: str) -> bool:
    try:
        if is_pg:
            # Use information_schema for PostgreSQL
            result = conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (table,)
            )
            return result.fetchone() is not None
        else:
            result = conn.execute(f"SELECT 1 FROM {table} LIMIT 0")  # noqa: S608
            result.close()
            return True
    except Exception:
        return False


def run_migrations(app) -> None:
    """Run all pending migrations inside the given Flask app context."""
    with app.app_context():
        from extensions import db

        engine = db.engine
        is_pg = "postgresql" in str(engine.url)

        with engine.begin() as conn:
            # ── 1. Create all tables that don't exist yet ─────────────────
            # SQLAlchemy's create_all is already idempotent (uses IF NOT EXISTS).
            db.create_all()
            log.info("create_all() complete – all declared tables exist.")

            # ── 2. Add columns that may be missing from pre-existing tables ─
            # This handles the case where the DB was created before a column
            # was added to the model.

            migrations: list[tuple[str, str, str]] = [
                # (table, column, column_definition)
                # candidate_job_evaluations
                ("candidate_job_evaluations", "eval_status",      "VARCHAR(32) DEFAULT 'pending'"),
                ("candidate_job_evaluations", "eval_error",       "TEXT"),
                ("candidate_job_evaluations", "strengths",        "TEXT"),   # JSON stored as TEXT in SQLite
                ("candidate_job_evaluations", "gaps",             "TEXT"),
                ("candidate_job_evaluations", "why_fit",          "TEXT"),
                ("candidate_job_evaluations", "nd_inclusion",     "TEXT DEFAULT '{}'"),
                ("candidate_job_evaluations", "action_taken_at",  "TIMESTAMP"),
                ("candidate_job_evaluations", "evaluated_at",     "TIMESTAMP"),
                # jobs
                ("jobs", "skills_required",  "TEXT DEFAULT '[]'"),
                ("jobs", "inclusion_settings", "TEXT DEFAULT '{}'"),
                ("jobs", "requirements",     "TEXT DEFAULT '[]'"),
                ("jobs", "employment_type",  "VARCHAR(64) DEFAULT 'Full-time'"),
                ("jobs", "salary_min",       "INTEGER"),
                ("jobs", "salary_max",       "INTEGER"),
                ("jobs", "is_active",        "BOOLEAN DEFAULT TRUE NOT NULL"),
                ("jobs", "region_id",        "INTEGER REFERENCES regions(id)"),
                # scraped_jobs
                ("scraped_jobs", "salary",    "VARCHAR(128)"),
                ("scraped_jobs", "source",    "VARCHAR(64) DEFAULT 'remoteok'"),
                ("scraped_jobs", "posted_at", "TIMESTAMP"),
                ("scraped_jobs", "is_active", "BOOLEAN DEFAULT TRUE NOT NULL"),
                ("scraped_jobs", "region_id", "INTEGER REFERENCES regions(id)"),
                # candidates
                ("candidates", "projects",                "TEXT DEFAULT '[]'"),
                ("candidates", "neurodivergent",          "BOOLEAN DEFAULT NULL"),
                ("candidates", "nd_type",                 "VARCHAR(50) DEFAULT NULL"),
                ("candidates", "github_username",        "VARCHAR(128)"),
                ("candidates", "leetcode_username",      "VARCHAR(128)"),
                ("candidates", "resume_url",             "VARCHAR(512)"),
                ("candidates", "github_repos",           "INTEGER"),
                ("candidates", "github_stars",           "INTEGER"),
                ("candidates", "github_forks",           "INTEGER"),
                ("candidates", "github_top_languages",   "TEXT DEFAULT '[]'"),
                ("candidates", "github_repos_data",      "TEXT DEFAULT '[]'"),
                ("candidates", "lc_easy",                "INTEGER"),
                ("candidates", "lc_medium",              "INTEGER"),
                ("candidates", "lc_hard",                "INTEGER"),
                ("candidates", "lc_rating",              "FLOAT"),
                ("candidates", "resume_skills",          "TEXT DEFAULT '[]'"),
                ("candidates", "resume_projects",        "TEXT DEFAULT '[]'"),
                ("candidates", "resume_years_experience","INTEGER"),
                ("candidates", "enrichment_status",      "VARCHAR(32) DEFAULT 'none'"),
                ("candidates", "enrichment_error",       "TEXT"),
                ("candidates", "enriched_at",            "TIMESTAMP"),
                ("candidates", "agent_statuses",         "TEXT DEFAULT '{}'"),
                ("candidates", "top_job_matches",        "TEXT DEFAULT '[]'"),
                ("candidates", "preferred_region_id",    "INTEGER REFERENCES regions(id)"),
                # feedback_reports
                ("feedback_reports", "evaluation_id",         "INTEGER UNIQUE NOT NULL REFERENCES candidate_job_evaluations(id) ON DELETE CASCADE"),
                ("feedback_reports", "candidate_report",      "TEXT"),
                ("feedback_reports", "recruiter_summary",     "TEXT"),
                ("feedback_reports", "interview_questions",   "TEXT DEFAULT '[]'"),
                ("feedback_reports", "fairness_assessment",   "TEXT"),
                ("feedback_reports", "learning_resources",    "TEXT DEFAULT '{}'"),
                ("feedback_reports", "task_checklist",        "TEXT DEFAULT '[]'"),
                ("feedback_reports", "generated_at",          "TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL"),
                ("feedback_reports", "generation_time_ms",    "INTEGER"),
                # messages
                ("messages", "subject", "VARCHAR(255) DEFAULT 'New Message'"),
            ]

            added = 0
            for table, column, col_def in migrations:
                # if not _table_exists(conn, table):
                #     log.info("  skip (table %s does not exist yet)", table)
                #     continue
                # if _column_exists(conn, table, column):
                #     continue
                try:
                    if is_pg:
                        from sqlalchemy import text
                        conn.execute(
                            text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_def}")
                        )
                    else:
                        conn.execute(
                            f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"  # noqa: S608
                        )
                    log.info("  + %s.%s", table, column)
                    added += 1
                except Exception as exc:
                    # Column may have been added by a concurrent process – ignore
                    log.warning("  could not add %s.%s: %s", table, column, exc)

            if added:
                log.info("Added %d missing column(s).", added)
            else:
                log.info("No missing columns – schema is up to date.")

        log.info("Migration complete.")


if __name__ == "__main__":
    # Bootstrap the Flask app so we have a DB connection
    try:
        from app import create_app
    except ImportError:
        log.error("Could not import create_app from app.py. Run this script from the Backend/ directory.")
        sys.exit(1)

    flask_app = create_app()
    run_migrations(flask_app)
    log.info("Done.")
