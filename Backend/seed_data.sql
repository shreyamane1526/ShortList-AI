-- Seed data for candidate_ai
-- Inserts two users (candidate + recruiter) and their profile rows.

BEGIN;

-- Users (no password_hash so you can set hashes manually or register via the app)
INSERT INTO users (email, full_name, role, auth_provider, created_at)
VALUES
  ('recruiter@example.com', 'John Recruiter', 'recruiter', 'local', NOW()),
  ('candidate@example.com', 'Alice Candidate', 'candidate', 'local', NOW());

-- Candidate profile linked to candidate@example.com
INSERT INTO candidates (user_id, headline, location, summary, years_experience, skills, links, created_at, updated_at)
SELECT id, 'Frontend Engineer', 'Bengaluru, IN', '5 years building web apps', 5, '["React","TypeScript","Node"]', '[]', NOW(), NOW()
FROM users WHERE email = 'candidate@example.com';

-- Recruiter profile linked to recruiter@example.com
INSERT INTO recruiters (user_id, company_name, job_title, created_at, updated_at)
SELECT id, 'Acme Corp', 'Senior Recruiter', NOW(), NOW()
FROM users WHERE email = 'recruiter@example.com';

COMMIT;
