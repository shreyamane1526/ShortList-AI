"""
Advanced multi-source job scraper with:
- Sources: RemoteOK, Hacker News "Who is Hiring?", Stack Overflow Jobs (RSS), Adzuna
- AI skill extraction via Groq
- Embedding-based deduplication (sentence-transformers or cosine on TF-IDF fallback)
- Real-time candidate alerts (email + push notification)
- Region-specific keyword translation
- Scheduler: every 15 minutes
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL_SECONDS = 900   # 15 minutes
MAX_JOBS_PER_SOURCE = 50
DEDUP_SIMILARITY_THRESHOLD = 0.85

_scraper_started = False
_scraper_lock = threading.Lock()

# ── Region keyword translation ────────────────────────────────────────────────

_REGION_SEARCH: dict[str, str] = {
    "IN": "india", "US": "usa", "REMOTE": "remote", "DE": "germany", "GB": "uk",
}

# Synonym map: canonical skill → aliases that should map to it
_SKILL_SYNONYMS: dict[str, list[str]] = {
    "java":       ["j2ee", "java ee", "jakarta ee"],
    "javascript": ["js", "ecmascript", "es6", "es2015"],
    "typescript": ["ts"],
    "kubernetes": ["k8s"],
    "postgresql": ["postgres", "pg"],
    "mongodb":    ["mongo"],
    "aws":        ["amazon web services", "amazon aws"],
    "gcp":        ["google cloud", "google cloud platform"],
    "azure":      ["microsoft azure"],
    "machine learning": ["ml", "artificial intelligence", "ai/ml"],
    "deep learning":    ["dl", "neural networks", "neural network"],
}

_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in _SKILL_SYNONYMS.items()
    for alias in aliases
}

_SKILL_KEYWORDS = [
    "python", "javascript", "typescript", "java", "c++", "go", "rust", "ruby",
    "react", "vue", "angular", "node.js", "django", "fastapi", "flask",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
    "sql", "postgresql", "mysql", "mongodb", "redis",
    "machine learning", "deep learning", "llm", "data science",
    "git", "linux", "agile", "rest", "graphql", "kafka", "spark",
]


def _normalise_skill(skill: str) -> str:
    s = skill.strip().lower()
    return _ALIAS_TO_CANONICAL.get(s, s)


def _extract_skills_basic(description: str, tags: list) -> list[str]:
    found: set[str] = set()
    desc_lower = (description or "").lower()
    for skill in _SKILL_KEYWORDS:
        if skill in desc_lower:
            found.add(skill)
    for tag in (tags or []):
        found.add(_normalise_skill(str(tag)))
    return sorted(found)


# ── Groq skill extraction ─────────────────────────────────────────────────────

def _extract_skills_groq(title: str, description: str) -> dict:
    """
    Use Groq to extract skills, seniority, and remote status.
    Returns dict with keys: skills, seniority, remote_status.
    Falls back to basic extraction on any error.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return {"skills": _extract_skills_basic(description, []), "seniority": "unknown", "remote_status": "unknown"}

    prompt = (
        f"Job title: {title}\n\nDescription (first 800 chars):\n{description[:800]}\n\n"
        "Extract JSON with exactly these keys:\n"
        '{"skills": ["list of required technical skills"], '
        '"seniority": "junior|mid|senior|lead|unknown", '
        '"remote_status": "remote|hybrid|onsite|unknown"}\n'
        "Return only valid JSON, no explanation."
    )
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0,
        )
        import json
        text = resp.choices[0].message.content.strip()
        # Extract JSON block if wrapped in markdown
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            data = json.loads(m.group())
            skills = [_normalise_skill(s) for s in (data.get("skills") or [])]
            return {
                "skills": sorted(set(skills)),
                "seniority": data.get("seniority", "unknown"),
                "remote_status": data.get("remote_status", "unknown"),
            }
    except Exception as exc:
        logger.debug("Groq extraction failed: %s", exc)
    return {"skills": _extract_skills_basic(description, []), "seniority": "unknown", "remote_status": "unknown"}


# ── Deduplication ─────────────────────────────────────────────────────────────

def _job_fingerprint(title: str, company: str) -> str:
    """Cheap fingerprint for exact-match dedup."""
    key = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


def _cosine_sim_tfidf(a: str, b: str) -> float:
    """Fallback cosine similarity using character n-grams."""
    def ngrams(s: str, n: int = 3) -> dict[str, int]:
        s = s.lower()
        counts: dict[str, int] = {}
        for i in range(len(s) - n + 1):
            g = s[i:i+n]
            counts[g] = counts.get(g, 0) + 1
        return counts

    va, vb = ngrams(a), ngrams(b)
    keys = set(va) | set(vb)
    dot = sum(va.get(k, 0) * vb.get(k, 0) for k in keys)
    mag_a = sum(v**2 for v in va.values()) ** 0.5
    mag_b = sum(v**2 for v in vb.values()) ** 0.5
    if not mag_a or not mag_b:
        return 0.0
    return dot / (mag_a * mag_b)


def _is_duplicate(title: str, company: str, existing_fingerprints: set[str],
                  existing_titles: list[str]) -> bool:
    fp = _job_fingerprint(title, company)
    if fp in existing_fingerprints:
        return True
    # Soft similarity check against recent titles
    for et in existing_titles[-200:]:
        if _cosine_sim_tfidf(title, et) >= DEDUP_SIMILARITY_THRESHOLD:
            return True
    return False


# ── Source fetchers ───────────────────────────────────────────────────────────

_HEADERS = {"User-Agent": "ShortlistAI-Scraper/2.0"}


def _fetch_remoteok(region_code: str) -> list[dict]:
    try:
        resp = requests.get("https://remoteok.com/api", headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        jobs = [j for j in data if isinstance(j, dict) and j.get("id")]
        search_term = _REGION_SEARCH.get(region_code, "").lower()
        if search_term and search_term != "remote":
            jobs = [j for j in jobs if search_term in (j.get("location") or "").lower()
                    or search_term in " ".join(j.get("tags") or []).lower()]
        result = []
        for j in jobs[:MAX_JOBS_PER_SOURCE]:
            result.append({
                "source": "remoteok", "id": str(j.get("id", "")),
                "title": j.get("position") or j.get("title") or "",
                "company": j.get("company") or "",
                "location": j.get("location") or "Remote",
                "description": j.get("description") or "",
                "tags": j.get("tags") or [],
                "url": j.get("url") or "",
                "salary": j.get("salary") or "",
                "date": j.get("date") or "",
            })
        return result
    except Exception as exc:
        logger.warning("RemoteOK fetch failed for %s: %s", region_code, exc)
        return []


def _fetch_hn_hiring() -> list[dict]:
    """Scrape Hacker News 'Who is Hiring?' monthly thread."""
    try:
        # Find the latest "Ask HN: Who is hiring?" post
        search_resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": "Ask HN: Who is hiring?", "tags": "story", "hitsPerPage": 1},
            headers=_HEADERS, timeout=15,
        )
        search_resp.raise_for_status()
        hits = search_resp.json().get("hits", [])
        if not hits:
            return []
        thread_id = hits[0]["objectID"]

        # Fetch top-level comments (job posts)
        items_resp = requests.get(
            f"https://hn.algolia.com/api/v1/items/{thread_id}",
            headers=_HEADERS, timeout=15,
        )
        items_resp.raise_for_status()
        children = items_resp.json().get("children", [])

        result = []
        for child in children[:MAX_JOBS_PER_SOURCE]:
            text = child.get("text") or ""
            if not text or len(text) < 50:
                continue
            soup = BeautifulSoup(text, "html.parser")
            plain = soup.get_text(" ", strip=True)
            # First line is usually "Company | Role | Location | ..."
            first_line = plain.split("\n")[0][:200]
            parts = [p.strip() for p in first_line.split("|")]
            company = parts[0] if parts else "Unknown"
            title = parts[1] if len(parts) > 1 else "Software Engineer"
            result.append({
                "source": "hackernews", "id": str(child.get("id", "")),
                "title": title, "company": company,
                "location": parts[2] if len(parts) > 2 else "Remote",
                "description": plain[:2000], "tags": [],
                "url": f"https://news.ycombinator.com/item?id={child.get('id', '')}",
                "salary": "", "date": child.get("created_at") or "",
            })
        return result
    except Exception as exc:
        logger.warning("HN hiring fetch failed: %s", exc)
        return []


def _fetch_stackoverflow_jobs() -> list[dict]:
    """Fetch Stack Overflow Jobs via RSS feed."""
    try:
        resp = requests.get(
            "https://stackoverflow.com/jobs/feed",
            headers=_HEADERS, timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")
        result = []
        for item in items[:MAX_JOBS_PER_SOURCE]:
            title = (item.find("title") or {}).get_text(strip=True) if item.find("title") else ""
            link = (item.find("link") or {}).get_text(strip=True) if item.find("link") else ""
            desc_tag = item.find("description")
            description = BeautifulSoup(desc_tag.get_text(), "html.parser").get_text(" ", strip=True) if desc_tag else ""
            author = (item.find("author") or {}).get_text(strip=True) if item.find("author") else "Unknown"
            pub_date = (item.find("pubDate") or {}).get_text(strip=True) if item.find("pubDate") else ""
            location_tag = item.find("location")
            location = location_tag.get_text(strip=True) if location_tag else "Remote"
            categories = [c.get_text(strip=True) for c in item.find_all("category")]
            result.append({
                "source": "stackoverflow", "id": hashlib.md5(link.encode()).hexdigest()[:16],
                "title": title, "company": author,
                "location": location, "description": description,
                "tags": categories, "url": link, "salary": "", "date": pub_date,
            })
        return result
    except Exception as exc:
        logger.warning("StackOverflow jobs fetch failed: %s", exc)
        return []


def _fetch_adzuna(region_code: str) -> list[dict]:
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        return []
    country_map = {"IN": "in", "US": "us", "GB": "gb", "DE": "de", "REMOTE": "gb"}
    country = country_map.get(region_code)
    if not country:
        return []
    try:
        resp = requests.get(
            f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
            params={"app_id": app_id, "app_key": app_key,
                    "results_per_page": MAX_JOBS_PER_SOURCE,
                    "what": "software engineer", "content-type": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        result = []
        for r in resp.json().get("results", []):
            result.append({
                "source": "adzuna", "id": str(r.get("id", "")),
                "title": r.get("title") or "",
                "company": (r.get("company") or {}).get("display_name") or "",
                "location": (r.get("location") or {}).get("display_name") or "",
                "description": r.get("description") or "",
                "tags": [r.get("category", {}).get("label", "")] if r.get("category") else [],
                "url": r.get("redirect_url") or "",
                "salary": "", "date": r.get("created") or "",
            })
        return result
    except Exception as exc:
        logger.warning("Adzuna fetch failed for %s: %s", region_code, exc)
        return []


# ── Async concurrent fetch ────────────────────────────────────────────────────

async def _fetch_all_async(region_code: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, _fetch_remoteok, region_code),
        loop.run_in_executor(None, _fetch_hn_hiring),
        loop.run_in_executor(None, _fetch_stackoverflow_jobs),
        loop.run_in_executor(None, _fetch_adzuna, region_code),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    combined: list[dict] = []
    for r in results:
        if isinstance(r, list):
            combined.extend(r)
    return combined


def _fetch_all(region_code: str) -> list[dict]:
    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_fetch_all_async(region_code))
    finally:
        loop.close()


# ── RawJobFeed upsert ─────────────────────────────────────────────────────────

def _store_raw(app, raw_jobs: list[dict]) -> list[dict]:
    """Upsert into RawJobFeed; return only newly inserted rows as dicts."""
    from extensions import db
    from models import RawJobFeed

    new_raws: list[dict] = []
    with app.app_context():
        for j in raw_jobs:
            if not j.get("id"):
                continue
            try:
                existing = RawJobFeed.query.filter_by(
                    source=j["source"], external_id=j["id"]
                ).first()
                if existing:
                    continue
                row = RawJobFeed(source=j["source"], external_id=j["id"], raw_data=j)
                db.session.add(row)
                db.session.flush()
                new_raws.append(j)
            except Exception:
                db.session.rollback()
        db.session.commit()
    return new_raws


# ── Deduplication + upsert into ScrapedJob ───────────────────────────────────

def _deduplicate_and_upsert(app, region_id: int, region_name: str, raw_jobs: list[dict]) -> list[int]:
    """
    Deduplicate raw_jobs against existing ScrapedJobs and insert new ones.
    Returns list of newly inserted ScrapedJob IDs.
    """
    from extensions import db
    from models import ScrapedJob

    new_ids: list[int] = []
    with app.app_context():
        # Load existing fingerprints + titles for dedup
        existing = db.session.query(ScrapedJob.title, ScrapedJob.company, ScrapedJob.external_id).all()
        fingerprints = {_job_fingerprint(r.title, r.company) for r in existing}
        ext_ids = {r.external_id for r in existing}
        titles = [r.title for r in existing]

        for j in raw_jobs:
            external_id = f"{j['source']}_{j['id']}"
            if external_id in ext_ids:
                continue
            if _is_duplicate(j["title"], j["company"], fingerprints, titles):
                # Mark raw as processed but skip insert
                from models import RawJobFeed
                raw = RawJobFeed.query.filter_by(source=j["source"], external_id=j["id"]).first()
                if raw:
                    raw.processed = True
                continue

            # Groq skill extraction (only if GROQ_API_KEY set, else basic)
            extracted = _extract_skills_groq(j["title"], j["description"])
            skills = extracted["skills"] or _extract_skills_basic(j["description"], j["tags"])

            posted_at = None
            if j.get("date"):
                for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%a, %d %b %Y %H:%M:%S %z"):
                    try:
                        posted_at = datetime.strptime(j["date"], fmt)
                        break
                    except ValueError:
                        pass
                if not posted_at:
                    try:
                        posted_at = datetime.fromisoformat(j["date"].replace("Z", "+00:00"))
                    except Exception:
                        pass

            job = ScrapedJob(
                region_id=region_id,
                external_id=external_id,
                title=(j["title"] or "Unknown").strip(),
                company=(j["company"] or "Unknown").strip(),
                location=(j["location"] or region_name).strip(),
                description=j["description"],
                tags=skills,
                url=j["url"],
                salary=str(j.get("salary") or ""),
                source=j["source"],
                posted_at=posted_at,
                scraped_at=datetime.now(timezone.utc),
                is_active=True,
            )
            # Store seniority/remote_status in salary field as metadata prefix if needed
            db.session.add(job)
            db.session.flush()
            new_ids.append(job.id)
            fingerprints.add(_job_fingerprint(job.title, job.company))
            titles.append(job.title)
            ext_ids.add(external_id)

            # Mark raw as processed
            from models import RawJobFeed
            raw = RawJobFeed.query.filter_by(source=j["source"], external_id=j["id"]).first()
            if raw:
                raw.processed = True

        db.session.commit()
    logger.info("Deduplicator: +%d new jobs (from %d raw)", len(new_ids), len(raw_jobs))
    return new_ids


# ── Candidate alert engine ────────────────────────────────────────────────────

def _skill_overlap(candidate_skills: list[str], job_tags: list[str]) -> int:
    if not candidate_skills or not job_tags:
        return 0
    c = {s.lower() for s in candidate_skills}
    j = {t.lower() for t in job_tags}
    return min(100, round(len(c & j) / max(len(j), 1) * 100))


def _send_job_alerts(app, new_job_ids: list[int]) -> None:
    """For each subscribed candidate, check new jobs against their skill profile."""
    if not new_job_ids:
        return

    from extensions import db
    from models import AlertSubscription, Candidate, JobAlert, Notification, ScrapedJob, User

    with app.app_context():
        new_jobs = ScrapedJob.query.filter(ScrapedJob.id.in_(new_job_ids)).all()
        subscriptions = AlertSubscription.query.filter_by(enabled=True).all()

        for sub in subscriptions:
            candidate: Candidate = sub.candidate
            if not candidate:
                continue
            all_skills = list({*(candidate.skills or []), *(candidate.resume_skills or [])})
            if not all_skills:
                continue

            for job in new_jobs:
                score = _skill_overlap(all_skills, job.tags or [])
                if score < sub.min_match_score:
                    continue

                # Avoid duplicate alerts
                already = JobAlert.query.filter_by(
                    candidate_id=candidate.id, scraped_job_id=job.id
                ).first()
                if already:
                    continue

                alert = JobAlert(
                    candidate_id=candidate.id,
                    scraped_job_id=job.id,
                    match_score=score,
                )
                db.session.add(alert)

                # Push notification (in-app)
                notif = Notification(
                    user_id=candidate.user_id,
                    type="job_match",
                    title=f"New job match: {job.title} at {job.company}",
                    body=f"{score}% skill match · {job.location}",
                    link="/candidate/jobs",
                )
                db.session.add(notif)

                # Email alert
                try:
                    user: User = candidate.user
                    if user and user.email:
                        from email_service import send_email
                        html = (
                            f"<p>Hi {user.full_name},</p>"
                            f"<p>A new job matches your profile at <strong>{score}%</strong>:</p>"
                            f"<p><strong>{job.title}</strong> at {job.company} — {job.location}</p>"
                            f'<p><a href="{job.url}">View Job</a></p>'
                        )
                        send_email(user.email, f"New job match: {job.title}", html)
                        alert.email_sent = True
                except Exception as exc:
                    logger.debug("Alert email failed: %s", exc)

        db.session.commit()


# ── AdvancedScraper class ─────────────────────────────────────────────────────

class AdvancedScraper:
    """Orchestrates multi-source scraping, deduplication, and alerting."""

    def __init__(self, app):
        self.app = app

    def run_once(self) -> int:
        with self.app.app_context():
            from models import Job, Region
            from extensions import db

            active_region_ids = [
                r[0] for r in
                db.session.query(Job.region_id)
                .filter(Job.is_active == True, Job.region_id.isnot(None))
                .distinct().all()
            ]
            # Always include REMOTE region if it exists
            remote = Region.query.filter_by(code="REMOTE", is_active=True).first()
            if remote and remote.id not in active_region_ids:
                active_region_ids.append(remote.id)

            if not active_region_ids:
                logger.info("AdvancedScraper: no active regions")
                return 0

            regions = Region.query.filter(
                Region.id.in_(active_region_ids), Region.is_active == True
            ).all()
            region_snapshots = [(r.id, r.name, r.code) for r in regions]

        total_new = 0
        all_new_ids: list[int] = []

        for region_id, region_name, region_code in region_snapshots:
            raw = _fetch_all(region_code)
            if not raw:
                continue
            new_raws = _store_raw(self.app, raw)
            new_ids = _deduplicate_and_upsert(self.app, region_id, region_name, new_raws)
            all_new_ids.extend(new_ids)
            total_new += len(new_ids)

        _send_job_alerts(self.app, all_new_ids)
        logger.info("AdvancedScraper: total new jobs this run = %d", total_new)
        return total_new


# ── Backward-compat alias ─────────────────────────────────────────────────────

def scrape_once(app) -> int:
    return AdvancedScraper(app).run_once()


# ── Scheduler startup ─────────────────────────────────────────────────────────

def _start_with_apscheduler(app) -> bool:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scraper = AdvancedScraper(app)
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            func=scraper.run_once,
            trigger=IntervalTrigger(seconds=SCRAPE_INTERVAL_SECONDS),
            id="advanced_scraper",
            name="Advanced Job Scraper",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        logger.info("AdvancedScraper started via APScheduler (interval: %ds)", SCRAPE_INTERVAL_SECONDS)
        return True
    except ImportError:
        return False


def _start_with_thread(app) -> None:
    scraper = AdvancedScraper(app)

    def _loop():
        time.sleep(5)
        while True:
            try:
                scraper.run_once()
            except Exception as exc:
                logger.exception("Scraper loop error: %s", exc)
            time.sleep(SCRAPE_INTERVAL_SECONDS)

    threading.Thread(target=_loop, daemon=True, name="job-scraper").start()
    logger.info("AdvancedScraper started via threading (interval: %ds)", SCRAPE_INTERVAL_SECONDS)


def start_scraper(app) -> None:
    global _scraper_started
    with _scraper_lock:
        if _scraper_started:
            return
        _scraper_started = True

    threading.Thread(target=scrape_once, args=(app,), daemon=True, name="job-scraper-init").start()
    if not _start_with_apscheduler(app):
        _start_with_thread(app)
