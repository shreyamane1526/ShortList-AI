"""
Migration: add raw_job_feeds, job_alerts, alert_subscriptions tables.
Run from Backend/ directory:
    python migrate_job_alerts.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from extensions import db

def run():
    app = create_app()
    with app.app_context():
        # Import models so SQLAlchemy knows about the new tables
        from models import RawJobFeed, JobAlert, AlertSubscription  # noqa: F401
        db.create_all()
        print("✅  Tables created (or already exist):")
        print("   - raw_job_feeds")
        print("   - job_alerts")
        print("   - alert_subscriptions")

if __name__ == "__main__":
    run()
