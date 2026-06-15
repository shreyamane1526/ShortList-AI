# Shortlist AI — Frontend

React + Vite + Tailwind frontend for the Shortlist AI hiring platform.

## Quick Start

```bash
cd frontend
npm install
npm run dev        # starts on http://localhost:8080
```

The Vite dev server proxies `/api/*` → `http://localhost:5000` (Flask backend).

## Backend must be running first

```bash
cd Backend
pip install -r requirements.txt
python migrate_add_posted_at.py   # run once to fix DB schema
python app.py                     # starts on http://localhost:5000
```

## Environment

Copy `Backend/.env.example` → `Backend/.env` and fill in:

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | ✅ | Any random string |
| `JWT_SECRET_KEY` | ✅ | Any random string |
| `DATABASE_URL` | ✅ | PostgreSQL or SQLite |
| `GROQ_API_KEY` | ✅ | For AI evaluation (free at console.groq.com) |
| `GITHUB_TOKEN` | Recommended | Raises rate limit 60→5000/hr |
| `GOOGLE_CLIENT_ID/SECRET` | Optional | For Google OAuth |
| `SENDGRID_API_KEY` or `SMTP_*` | Optional | For email notifications |
| `ADZUNA_APP_ID/KEY` | Optional | For job scraping |
| `FRONTEND_URL` | ✅ | `http://localhost:8080` |

## Features

- **Auth**: Email/password + Google OAuth, role-based (candidate/recruiter)
- **Candidate**: Onboarding → AI enrichment (GitHub + LeetCode + Resume) → Job feed → Applications → Feedback
- **Recruiter**: Post jobs → View all candidates → AI evaluate → Shortlist/Reject → Message
- **Real-time**: Polls enrichment every 2.5s, evaluations every 3s, notifications every 15s
- **Messaging**: Full inbox with real email notifications via SendGrid/SMTP
- **Job Scraper**: RemoteOK + Adzuna, runs every 10 minutes
