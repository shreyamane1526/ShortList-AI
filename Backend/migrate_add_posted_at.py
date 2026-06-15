"""
Migration: Ensure scraped_jobs.posted_at column exists.
Run once: python migrate_add_posted_at.py

Safe to run multiple times (checks before adding).
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def run():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check scraped_jobs table
        if 'scraped_jobs' not in inspector.get_table_names():
            print("scraped_jobs table does not exist yet — running db.create_all()")
            db.create_all()
            print("Done.")
            return

        cols = {c['name'] for c in inspector.get_columns('scraped_jobs')}
        
        added = []
        # Detect dialect for type compatibility
        dialect = db.engine.dialect.name  # 'postgresql' or 'sqlite'
        ts_type = "TIMESTAMP" if dialect == "sqlite" else "TIMESTAMP WITH TIME ZONE"

        with db.engine.connect() as conn:
            if 'posted_at' not in cols:
                conn.execute(text(f"ALTER TABLE scraped_jobs ADD COLUMN posted_at {ts_type}"))
                added.append('posted_at')
                print("Added: scraped_jobs.posted_at")
            
            if 'is_active' not in cols:
                conn.execute(text("ALTER TABLE scraped_jobs ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
                added.append('is_active')
                print("Added: scraped_jobs.is_active")
            
            if 'scraped_at' not in cols:
                conn.execute(text(f"ALTER TABLE scraped_jobs ADD COLUMN scraped_at {ts_type}"))
                added.append('scraped_at')
                print("Added: scraped_jobs.scraped_at")

            # Candidate enrichment columns (safe to add if missing)
            cand_cols = {c['name'] for c in inspector.get_columns('candidates')}
            cand_additions = [
                ('github_forks',        'INTEGER'),
                ('github_repos_data',   'TEXT'),   # JSON stored as TEXT in SQLite
                ('resume_projects',     'TEXT'),
                ('agent_statuses',      'TEXT'),
                ('top_job_matches',     'TEXT'),
                ('enrichment_error',    'TEXT'),
                ('enriched_at',         ts_type),
            ]
            for col, typ in cand_additions:
                if col not in cand_cols:
                    conn.execute(text(f"ALTER TABLE candidates ADD COLUMN {col} {typ}"))
                    added.append(f'candidates.{col}')
                    print(f"Added: candidates.{col}")

            conn.commit()

        if added:
            print(f"\nMigration complete. Added {len(added)} column(s): {', '.join(added)}")
        else:
            print("All columns already exist. Nothing to do.")

if __name__ == '__main__':
    run()
