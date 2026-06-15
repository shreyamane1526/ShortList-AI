# fix_admin.py
from core.database import engine
from sqlmodel import text
from werkzeug.security import generate_password_hash

email = "admin@shortlist.ai"
password = "Admin123"
hashed = generate_password_hash(password)

with engine.connect() as conn:
    # Check if user exists
    result = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
    if result.first():
        print("User exists, updating password hash...")
        conn.execute(text("UPDATE users SET password_hash = :pwd WHERE email = :email"), {"pwd": hashed, "email": email})
    else:
        conn.execute(
            text("INSERT INTO users (email, full_name, password_hash, role, is_active) VALUES (:email, :name, :pwd, 'superadmin', true)"),
            {"email": email, "name": "System Admin", "pwd": hashed}
        )
    conn.commit()
    print(f"✅ Superadmin ready – email: {email}, password: {password}")