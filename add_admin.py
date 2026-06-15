from core.database import engine
from sqlmodel import text
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"])
hashed = pwd.hash("Admin123")

with engine.connect() as conn:
    conn.execute(
        text("""
        INSERT INTO users (email, full_name, password_hash, role, is_active)
        VALUES ('admin@shortlist.ai', 'System Admin', :pwd, 'superadmin', true)
        ON CONFLICT (email) DO NOTHING
        """),
        {"pwd": hashed},
    )
    conn.commit()

print("Superadmin created with password: Admin123")