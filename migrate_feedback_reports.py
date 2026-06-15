"""
migrate_feedback_reports.py
===========================
One-shot migration: adds the `feedback_reports` table used by Agent 5.

Works with both SQLite (dev) and PostgreSQL (prod).

Usage
-----
  # From the project root:
  python migrate_feedback_reports.py

  # Dry-run (print SQL only, don't execute):
  python migrate_feedback_reports.py --dry-run

What it does
------------
  1. Connects to the database configured in DATABASE_URL (or SQLite fallback).
  2. Checks whether `feedback_reports` already exists.
  3. If not, creates it with the schema below.
  4. If it already exists, prints a message and exits cleanly.

Table schema
------------
  feedback_reports
    id                 INTEGER  PRIMARY KEY AUTOINCREMENT
    evaluation_id      TEXT     NOT NULL UNIQUE INDEX   -- "<jd_hash>:<candidate_id>"
    feedback_json      TEXT     NOT NULL                -- full JSON blob
    confidence_score   INTEGER                          -- 0-100
    confidence_level   TEXT                             -- Low / Medium / High
    badges_json        TEXT                             -- JSON array of badge strings
    generated_at       DATETIME NOT NULL DEFAULT NOW
    generation_time_ms INTEGER
"""
from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv
load_dotenv()

from core.config import settings


# ── SQL templates ──────────────────────────────────────────────────────────────

_CREATE_SQLITE = """
CREATE TABLE IF NOT EXISTS feedback_reports (
    id                 INTEGER  PRIMARY KEY AUTOINCREMENT,
    evaluation_id      TEXT     NOT NULL UNIQUE,
    feedback_json      TEXT     NOT NULL,
    confidence_score   INTEGER,
    confidence_level   TEXT,
    badges_json        TEXT,
    generated_at       DATETIME NOT NULL DEFAULT (datetime('now')),
    generation_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS ix_feedback_reports_evaluation_id
    ON feedback_reports (evaluation_id);
""".strip()

_CREATE_POSTGRES = """
CREATE TABLE IF NOT EXISTS feedback_reports (
    id                 SERIAL       PRIMARY KEY,
    evaluation_id      TEXT         NOT NULL UNIQUE,
    feedback_json      TEXT         NOT NULL,
    confidence_score   INTEGER,
    confidence_level   TEXT,
    badges_json        TEXT,
    generated_at       TIMESTAMP    NOT NULL DEFAULT NOW(),
    generation_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS ix_feedback_reports_evaluation_id
    ON feedback_reports (evaluation_id);
""".strip()

_CHECK_TABLE_SQLITE  = "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback_reports';"
_CHECK_TABLE_POSTGRES = "SELECT to_regclass('public.feedback_reports');"


# ── Main ───────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> None:
    is_pg = settings.is_postgres
    db_url = settings.DATABASE_URL

    print(f"Database : {'PostgreSQL' if is_pg else 'SQLite'}")
    print(f"URL      : {db_url[:40]}{'...' if len(db_url) > 40 else ''}")
    print()

    create_sql = _CREATE_POSTGRES if is_pg else _CREATE_SQLITE
    check_sql  = _CHECK_TABLE_POSTGRES if is_pg else _CHECK_TABLE_SQLITE

    if dry_run:
        print("── DRY RUN — SQL that would be executed ──────────────────────")
        print(create_sql)
        print("──────────────────────────────────────────────────────────────")
        return

    if is_pg:
        try:
            import psycopg2  # type: ignore
        except ImportError:
            print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
            sys.exit(1)

        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute(check_sql)
        exists = cur.fetchone()[0] is not None

        if exists:
            print("✓  feedback_reports table already exists — nothing to do.")
        else:
            for stmt in create_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt + ";")
            print("✓  feedback_reports table created successfully (PostgreSQL).")

        cur.close()
        conn.close()

    else:
        import sqlite3

        # Extract file path from sqlite:///./path
        db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute(check_sql)
        exists = cur.fetchone() is not None

        if exists:
            print("✓  feedback_reports table already exists — nothing to do.")
        else:
            # SQLite supports multiple statements in executescript
            conn.executescript(create_sql)
            conn.commit()
            print("✓  feedback_reports table created successfully (SQLite).")

        conn.close()

    print()
    print("Migration complete.")
    print()
    print("Next steps:")
    print("  1. Start the FastAPI server:  uvicorn api.main:app --reload")
    print("  2. Run a pipeline:            POST /evaluate")
    print("  3. Retrieve feedback:         GET  /api/feedback/<evaluation_id>")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add feedback_reports table")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print SQL without executing")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
