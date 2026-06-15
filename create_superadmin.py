"""
create_superadmin.py – Create a superadmin user without needing models.py
"""
# LinedInHackathon/create_superadmin.py
import sys
import os

# Add project root to path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from datetime import datetime
from sqlmodel import SQLModel, Field, Session, create_engine
from core.database import engine
from werkzeug.security import generate_password_hash

# Define User model locally (only the fields needed for superadmin)
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    password_hash: str
    role: str = Field(default="candidate")  # candidate | recruiter | superadmin
    auth_provider: str = Field(default="local")
    created_at: datetime = Field(default_factory=datetime.utcnow)

def create_superadmin(email: str, password: str, full_name: str):
    # Create table if it doesn't exist (only for the User model)
    SQLModel.metadata.create_all(engine, tables=[User.__table__])
    
    with Session(engine) as session:
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            print(f"❌ User with email {email} already exists.")
            return
        hashed = generate_password_hash(password)
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hashed,
            role="superadmin",
            auth_provider="local"
        )
        session.add(user)
        session.commit()
        print(f"✅ Superadmin created: {email} (role=superadmin)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    create_superadmin(args.email, args.password, args.name)