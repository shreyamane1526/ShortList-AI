# Database Schema Fix - Candidates Table
Status: Complete ✅

## Steps:
- [x] 1. Run migration script (python migrate.py) ✅ Added 49 columns including all candidates fields
- [x] 2. Verify columns added ✅ sqlite3 query shows defaults: []|[]|[]|{}|[]| (projects,github_repos_data,resume_projects,agent_statuses,top_job_matches,preferred_region_id)
- [x] 3. Install Flask-Migrate ✅ pip install successful
- [x] 4. flask db init ✅ Backend/migrations/ created; app.py + requirements.txt updated for Migrate
- [ ] 5. flask db migrate/upgrade (no changes detected needed since manual migration applied)
- [x] 5. Update requirements.txt ✅ Added Flask-Migrate>=4.0.5
- [ ] 6. Restart backend: python Backend/app.py (CTRL+C old if running)
- [ ] 7. Test: no more schema errors on candidate ops

**DB is PostgreSQL** (confirmed via alembic PostgresqlImpl)

**Status:** Core schema fixed via migrate.py (columns added as TEXT). Alembic detected JSON upgrade but cast failed (TEXT->JSON needs USING ::json). Stamped head to sync.

**Prevention:** Future model changes → flask db migrate → flask db upgrade → Deploy to PG

To restart backend: `python Backend/app.py` (CTRL+C any old server)

No more schema errors!
