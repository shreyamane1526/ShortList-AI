from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import wraps
from urllib.parse import urlencode

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for
import jwt
from jwt import InvalidTokenError
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, oauth
from models import AuditLog, Candidate, Recruiter, User
from serializers import user_to_dict


auth_bp = Blueprint("auth", __name__)

VALID_ROLES = {"candidate", "recruiter"}


# ─────────────────────────── JWT helpers ────────────────────────────────────

def _jwt_secret() -> str:
    return current_app.config["JWT_SECRET_KEY"]


def _jwt_exp_minutes() -> int:
    return int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES_MINUTES"])


def create_access_token(user: User) -> tuple[str, int]:
    expires_in = _jwt_exp_minutes() * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")
    return token, expires_in


def _user_from_bearer_token() -> User | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (InvalidTokenError, ValueError, TypeError):
        return None
    return db.session.get(User, user_id)


def current_user() -> User | None:
    user_from_token = _user_from_bearer_token()
    if user_from_token is not None:
        return user_from_token
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        return view(user, *args, **kwargs)
    return wrapped


# ─────────────────────────── session / response helpers ─────────────────────

def store_session(user: User) -> None:
    session["user_id"] = user.id
    session["role"] = user.role
    session.permanent = True


def _dashboard_path(role: str) -> str:
    return "/candidate" if role == "candidate" else "/dashboard"


def response_for_user(user: User):
    """JSON response used by email/password login and register."""
    access_token, expires_in = create_access_token(user)
    return jsonify(
        {
            "user": user_to_dict(user),
            "redirect": _dashboard_path(user.role),
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }
    )


def _get_role_from_request() -> str:
    """Read ?role= from query string or JSON body; default to 'candidate'."""
    role = (
        request.args.get("role")
        or (request.get_json(silent=True) or {}).get("role")
        or "candidate"
    )
    return role if role in VALID_ROLES else "candidate"


def _oauth_missing(provider: str):
    frontend = current_app.config["FRONTEND_URL"]
    return redirect(f"{frontend}/auth?error=oauth_not_configured&provider={provider}")


def _ensure_profile(user: User) -> None:
    """Create a Candidate or Recruiter profile row if one doesn't exist yet."""
    if user.role == "candidate" and not user.candidate:
        db.session.add(Candidate(user_id=user.id, skills=[], links=[]))
    elif user.role == "recruiter" and not user.recruiter:
        db.session.add(Recruiter(user_id=user.id))


def _auth_audit_log(user: User | None, action: str, entity_type: str = "security", details: dict | None = None) -> None:
    db.session.add(AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        details=details or {},
    ))


# ─────────────────────────── standard auth routes ───────────────────────────

@auth_bp.get("/me")
@login_required
def me(user: User):
    return jsonify({"user": user_to_dict(user)})


@auth_bp.get("/token")
@login_required
def token(user: User):
    access_token, expires_in = create_access_token(user)
    return jsonify(
        {"access_token": access_token, "token_type": "Bearer", "expires_in": expires_in}
    )


@auth_bp.get("/token/verify")
@login_required
def token_verify(user: User):
    return jsonify({"valid": True, "user": user_to_dict(user)})


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email     = (data.get("email") or "").strip().lower()
    password  = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    role      = data.get("role") if data.get("role") in VALID_ROLES else "candidate"

    if not email or not password or not full_name:
        return jsonify({"error": "full_name, email, and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with that email already exists"}), 409

    user = User(
        email=email,
        full_name=full_name,
        role=role,
        auth_provider="local",
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.flush()
    _ensure_profile(user)
    store_session(user)
    _auth_audit_log(user, "user_registered", "user", {"email": user.email, "role": user.role})
    db.session.commit()

    current_app.logger.info("Registered user %s as %s", user.email, user.role)
    return response_for_user(user), 201


@auth_bp.post("/login")
def login():
    import traceback as _tb
    try:
        data     = request.get_json(silent=True) or {}
        email    = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        user = User.query.filter_by(email=email).first()
        if user is None:
            return jsonify({
                "error": "No account found with this email. Please sign up first.",
                "code": "user_not_found",
            }), 404

        if not user.password_hash:
            return jsonify({
                "error": "This account uses Google or LinkedIn login. Please sign in with that provider.",
                "code": "oauth_account",
            }), 400

        if not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid email or password"}), 401

        user.last_login_at = datetime.utcnow()
        _ensure_profile(user)
        store_session(user)
        _auth_audit_log(user, "login_success", "security", {"email": user.email, "role": user.role})
        db.session.commit()

        current_app.logger.info("User logged in: %s", user.email)
        return response_for_user(user)

    except Exception as exc:
        _tb.print_exc()   # always visible in the terminal
        current_app.logger.exception("Login error for %s: %s", request.get_json(silent=True, force=True) or {}, exc)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"error": "Login failed due to a server error. Check the terminal for details.", "detail": str(exc)}), 500


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


# ─────────────────────────── Google OAuth ───────────────────────────────────

@auth_bp.get("/google/login")
def google_login():
    if not _google_configured():
        return _oauth_missing("Google")

    # Persist the chosen role across the OAuth redirect
    session["pending_role"] = _get_role_from_request()
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri, prompt="select_account")


@auth_bp.get("/google/callback")
def google_callback():
    if not _google_configured():
        return _oauth_missing("Google")

    try:
        oauth.google.authorize_access_token()
    except Exception as exc:
        current_app.logger.warning("Google OAuth token exchange failed: %s", exc)
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(f"{frontend}/auth?error=oauth_failed")

    try:
        profile = oauth.google.get("userinfo").json()
    except Exception as exc:
        current_app.logger.warning("Google userinfo fetch failed: %s", exc)
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(f"{frontend}/auth?error=oauth_failed")

    email      = (profile.get("email") or "").strip().lower()
    google_sub = profile.get("sub") or profile.get("id") or ""
    full_name  = (
        profile.get("name")
        or profile.get("given_name")
        or email.split("@")[0]
        or "Google User"
    )

    if not email:
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(f"{frontend}/auth?error=no_email")

    # Role: use pending_role only for NEW users; existing users keep their stored role
    pending_role = session.pop("pending_role", "candidate")

    user = User.query.filter(
        (User.email == email) | (User.google_sub == google_sub)
    ).first()

    if user is None:
        # Brand-new user — use the role they selected on the auth page
        user = User(
            email=email,
            full_name=full_name,
            role=pending_role,
            auth_provider="google",
            google_sub=google_sub,
        )
        db.session.add(user)
        db.session.flush()
        current_app.logger.info(
            "New user via Google: %s (role=%s)", user.email, user.role
        )
    else:
        # Existing user — NEVER overwrite their role; just update profile fields
        user.full_name = user.full_name or full_name
        user.auth_provider = "google"
        if not user.google_sub:
            user.google_sub = google_sub
        current_app.logger.info(
            "Existing user signed in via Google: %s (role=%s)", user.email, user.role
        )

    _ensure_profile(user)
    store_session(user)
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    # Embed the JWT in the redirect URL so the frontend can store it without
    # a second round-trip.  The token is short-lived and HTTPS-only in prod.
    access_token, expires_in = create_access_token(user)
    frontend = current_app.config["FRONTEND_URL"]
    params = urlencode({
        "status": "success",
        "token": access_token,
        "role": user.role,
    })
    return redirect(f"{frontend}/auth?{params}")


# ─────────────────────────── LinkedIn OAuth ─────────────────────────────────

@auth_bp.get("/linkedin/login")
def linkedin_login():
    if not _linkedin_configured():
        return _oauth_missing("LinkedIn")

    session["pending_role"] = _get_role_from_request()
    redirect_uri = url_for("auth.linkedin_callback", _external=True)
    return oauth.linkedin.authorize_redirect(redirect_uri)


@auth_bp.get("/linkedin/callback")
def linkedin_callback():
    if not _linkedin_configured():
        return _oauth_missing("LinkedIn")

    try:
        oauth.linkedin.authorize_access_token()
        profile = oauth.linkedin.get("v2/me").json()
        email_payload = oauth.linkedin.get(
            "v2/emailAddress?q=members&projection=(elements*(handle~))"
        ).json()
    except Exception as exc:
        current_app.logger.warning("LinkedIn OAuth failed: %s", exc)
        frontend = current_app.config["FRONTEND_URL"]
        return redirect(f"{frontend}/auth?error=oauth_failed")

    elements   = email_payload.get("elements") or []
    email      = ""
    if elements:
        handle = elements[0].get("handle~") or {}
        email  = (handle.get("emailAddress") or "").strip().lower()

    linkedin_id = profile.get("id") or ""
    first_name  = profile.get("localizedFirstName") or ""
    last_name   = profile.get("localizedLastName") or ""
    full_name   = (f"{first_name} {last_name}").strip() or email.split("@")[0] or "LinkedIn User"
    pending_role = session.pop("pending_role", "candidate")

    if not email:
        email = f"linkedin-{linkedin_id}@example.local"

    user = User.query.filter(
        (User.email == email) | (User.linkedin_id == linkedin_id)
    ).first()

    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            role=pending_role,
            auth_provider="linkedin",
            linkedin_id=linkedin_id,
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.full_name = user.full_name or full_name
        user.auth_provider = "linkedin"
        if not user.linkedin_id:
            user.linkedin_id = linkedin_id

    _ensure_profile(user)
    store_session(user)
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    current_app.logger.info("LinkedIn sign-in: %s (role=%s)", user.email, user.role)

    access_token, _ = create_access_token(user)
    frontend = current_app.config["FRONTEND_URL"]
    params = urlencode({
        "status": "success",
        "token": access_token,
        "role": user.role,
    })
    return redirect(f"{frontend}/auth?{params}")


# ─────────────────────────── private helpers ────────────────────────────────

def _google_configured() -> bool:
    return bool(
        current_app.config.get("GOOGLE_CLIENT_ID")
        and current_app.config.get("GOOGLE_CLIENT_SECRET")
        and hasattr(oauth, "google")
    )


def _linkedin_configured() -> bool:
    return bool(
        current_app.config.get("LINKEDIN_CLIENT_ID")
        and current_app.config.get("LINKEDIN_CLIENT_SECRET")
        and hasattr(oauth, "linkedin")
    )
