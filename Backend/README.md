# Backend README

This file covers backend-specific setup and database instructions for developers.

## Quick Backend Setup

1. Create and activate a virtual environment

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\activate    # Windows PowerShell
# or on macOS / Linux
# source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. If you see missing modules when starting the app (e.g. `ModuleNotFoundError: No module named 'requests'`), make sure the venv is active and run:

```bash
pip install requests
```

## Configure environment

Copy the example env and edit it:

```bash
copy .env.example .env   # Windows
# or
cp .env.example .env     # macOS / Linux
```

Edit `Backend/.env` and set:

- `DATABASE_URL` — connection string for Postgres, e.g. `postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/candidate_ai`
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` — if you want Google OAuth enabled
- `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` — if you want LinkedIn OAuth enabled

> Do NOT commit `.env` to source control. Use `.env.example` as the template for collaborators.

## Database: creating vs using existing

### Create database from scratch

Replace `YOUR_POSTGRES_PASSWORD` with your postgres user password.

```powershell
$env:PGPASSWORD='YOUR_POSTGRES_PASSWORD'; psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE candidate_ai;"
$env:PGPASSWORD='YOUR_POSTGRES_PASSWORD'; psql -U postgres -h localhost -p 5432 -d candidate_ai -f init_db.sql
```

### If `candidate_ai` already exists (only want sample rows)

```powershell
$env:PGPASSWORD='YOUR_POSTGRES_PASSWORD'; psql -U postgres -h localhost -p 5432 -d candidate_ai -f seed_data.sql
```

### Set a usable password for a seeded user

To allow signing in with an email/password account created via the seed, generate a werkzeug password hash and update the DB.

```powershell
# generate a hash in the venv
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('password123'))"
# copy the printed hash and then run (replace PASTE_HASH and the email):
$env:PGPASSWORD='YOUR_POSTGRES_PASSWORD'; psql -U postgres -h localhost -p 5432 -d candidate_ai -c "UPDATE users SET password_hash = 'PASTE_HASH' WHERE email = 'candidate@example.com';"
```

## Start the backend

```bash
# with venv active
python run.py
```

The app runs on `http://localhost:5000`. If you need to run on a different host/port, edit `run.py`.

## Google OAuth troubleshooting

If you see `redirect_uri_mismatch` from Google when signing in:

1. Open Google Cloud Console → APIs & Services → Credentials → select your OAuth client.
2. Under **Authorized redirect URIs** add:
   - `http://localhost:5000/api/auth/google/callback`
   - `http://127.0.0.1:5000/api/auth/google/callback`
3. Save changes and wait a few seconds.

You can verify what redirect URI the app is sending by running (after backend is running):

```powershell
curl -I "http://localhost:5000/api/auth/google/login?role=candidate"
```

Look for the `Location:` header and the `redirect_uri=` parameter it contains — that exact value must be listed in Google Console.

## Files to edit

- `Backend/.env` — for secrets and DB connection
- `Frontend` — no special environment required by default; `VITE_API_BASE_URL` can be set if not using the dev proxy

## Seed data

- `Backend/seed_data.sql` contains sample users and profiles
- `Backend/init_db.sql` contains the schema creation statements

## Common troubleshooting

- `ModuleNotFoundError`: activate `.venv` and `pip install -r requirements.txt`
- `psql: FATAL: password authentication failed`: ensure `DATABASE_URL` password matches your Postgres password or adjust your PostgreSQL user settings
- `Google redirect_uri_mismatch`: add the exact redirect URI shown in the app to Google Console (see section above)

---

If you want, I can also:
- Add a small Python script to seed the DB and set password hashes automatically
- Add a single-command `setup.sh` / `setup.ps1` to automate venv + install + DB init

Tell me which automation you'd like and I'll add it.
