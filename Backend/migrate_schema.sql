-- migrate_schema.sql
-- Safe migration: adds every column the models expect.
-- Uses "ADD COLUMN IF NOT EXISTS" so it's safe to run multiple times.
-- Run with:  psql $DATABASE_URL -f migrate_schema.sql

-- ── candidates ───────────────────────────────────────────────────────────────
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS github_username        VARCHAR(128);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS leetcode_username      VARCHAR(128);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS resume_url             VARCHAR(512);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS github_repos           INTEGER;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS github_stars           INTEGER;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS github_forks           INTEGER;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS github_top_languages   JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS github_repos_data      JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS lc_easy                INTEGER;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS lc_medium              INTEGER;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS lc_hard                INTEGER;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS lc_rating              DOUBLE PRECISION;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS resume_skills          JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS resume_years_experience INTEGER;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS resume_projects        JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS enrichment_status      VARCHAR(32) DEFAULT 'none';
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS enrichment_error       TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS enriched_at            TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS agent_statuses         JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS top_job_matches        JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS preferred_region_id    INTEGER REFERENCES regions(id) ON DELETE SET NULL;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS projects               JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS neurodivergent         BOOLEAN DEFAULT NULL;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS nd_type                VARCHAR(50) DEFAULT NULL;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS links                  JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS skills                 JSON;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS headline               VARCHAR(255);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS location               VARCHAR(255);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS summary                TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS years_experience       INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS inclusion_settings           JSON DEFAULT '{}';
ALTER TABLE candidate_job_evaluations ADD COLUMN IF NOT EXISTS nd_inclusion JSON DEFAULT '{}';

-- ── users ────────────────────────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub    VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_id   VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(32) DEFAULT 'local';

-- ── candidate_job_evaluations ────────────────────────────────────────────────
ALTER TABLE candidate_job_evaluations ADD COLUMN IF NOT EXISTS eval_error       TEXT;
ALTER TABLE candidate_job_evaluations ADD COLUMN IF NOT EXISTS recruiter_action VARCHAR(32) DEFAULT 'pending';
ALTER TABLE candidate_job_evaluations ADD COLUMN IF NOT EXISTS action_taken_at  TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE candidate_job_evaluations ADD COLUMN IF NOT EXISTS evaluated_at     TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE candidate_job_evaluations ADD COLUMN IF NOT EXISTS why_fit          TEXT;
ALTER TABLE candidate_job_evaluations ADD COLUMN IF NOT EXISTS strengths        JSON;
ALTER TABLE candidate_job_evaluations ADD COLUMN IF NOT EXISTS gaps             JSON;

-- ── feedback_reports (create if missing) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback_reports (
    id                  SERIAL PRIMARY KEY,
    evaluation_id       INTEGER NOT NULL UNIQUE REFERENCES candidate_job_evaluations(id) ON DELETE CASCADE,
    candidate_report    TEXT,
    recruiter_summary   TEXT,
    interview_questions JSON,
    fairness_assessment TEXT,
    learning_resources  JSON,
    task_checklist      JSON,
    generated_at        TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    generation_time_ms  INTEGER
);
CREATE INDEX IF NOT EXISTS ix_feedback_reports_evaluation_id ON feedback_reports(evaluation_id);

-- ── scraped_jobs ─────────────────────────────────────────────────────────────
ALTER TABLE scraped_jobs ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP WITHOUT TIME ZONE;

SELECT 'Migration complete' AS status;
