"""
Fix: Convert TEXT columns that should be JSON/JSONB to proper JSONB type.
Run once: python fix_json_columns.py

This fixes the issue where ALTER TABLE added columns as TEXT instead of JSONB,
causing SQLAlchemy to return JSON values as strings instead of dicts/lists.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

# Columns that must be JSONB (not TEXT)
CANDIDATE_JSON_COLS = [
    'github_top_languages',
    'github_repos_data',
    'resume_skills',
    'resume_projects',
    'agent_statuses',
    'top_job_matches',
    'skills',
    'links',
    'projects',
]

def run():
    app = create_app()
    with app.app_context():
        dialect = db.engine.dialect.name
        print(f"Database dialect: {dialect}")
        
        if dialect != 'postgresql':
            print("SQLite detected — JSON columns work differently, no migration needed.")
            print("SQLite stores JSON as TEXT natively and SQLAlchemy handles it correctly.")
            return
        
        inspector = inspect(db.engine)
        
        if 'candidates' not in inspector.get_table_names():
            print("candidates table not found — run the app first to create tables")
            return
        
        col_types = {c['name']: str(c['type']) for c in inspector.get_columns('candidates')}
        
        fixed = []
        with db.engine.connect() as conn:
            for col in CANDIDATE_JSON_COLS:
                if col not in col_types:
                    print(f"  SKIP {col} — column doesn't exist")
                    continue
                
                current_type = col_types[col].upper()
                if 'JSON' in current_type:
                    print(f"  OK   {col} — already {current_type}")
                    continue
                
                print(f"  FIX  {col} — converting {current_type} → JSONB")
                try:
                    # Each ALTER must be its own transaction in PostgreSQL
                    conn.execute(text("SAVEPOINT sp1"))
                    # Step 1: Drop the default (it can't be cast automatically)
                    conn.execute(text(f"ALTER TABLE candidates ALTER COLUMN {col} DROP DEFAULT"))
                    # Step 2: Convert TEXT → JSONB
                    conn.execute(text(f"""
                        ALTER TABLE candidates 
                        ALTER COLUMN {col} TYPE JSONB 
                        USING CASE 
                            WHEN {col} IS NULL THEN NULL
                            WHEN {col} = '' THEN '[]'::jsonb
                            ELSE {col}::jsonb
                        END
                    """))
                    # Step 3: Re-add the default as JSONB
                    default_val = "'[]'::jsonb" if col != 'agent_statuses' else "'{}'::jsonb"
                    conn.execute(text(f"ALTER TABLE candidates ALTER COLUMN {col} SET DEFAULT {default_val}"))
                    conn.execute(text("RELEASE SAVEPOINT sp1"))
                    fixed.append(col)
                    print(f"  ✅  {col} converted")
                except Exception as e:
                    conn.execute(text("ROLLBACK TO SAVEPOINT sp1"))
                    print(f"  ERROR converting {col}: {e}")
            
            conn.commit()
        
        if fixed:
            print(f"\n✅ Converted {len(fixed)} columns to JSONB: {', '.join(fixed)}")
        else:
            print("\n✅ All JSON columns already correct — nothing to do")

if __name__ == '__main__':
    run()
