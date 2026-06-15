"""
Migration script to add livekit_interviews table.

Run this once to create the table in your PostgreSQL database:
    python migrate_livekit.py
"""
from app import app, db
from models import LiveKitInterview

def migrate():
    with app.app_context():
        print("[Migrate] Creating livekit_interviews table...")
        db.create_all()
        print("[Migrate] ✓ Done. Table created successfully.")

if __name__ == "__main__":
    migrate()
