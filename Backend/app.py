from __future__ import annotations

import logging
from pathlib import Path

from authlib.integrations.flask_client import OAuthError
from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError

from api import api_bp
from auth import auth_bp
from config import Config
from extensions import db, oauth
from flask_migrate import Migrate

from scraper import start_scraper


def _register_oauth_clients(app: Flask) -> None:
    google_client_id     = app.config.get("GOOGLE_CLIENT_ID", "")
    google_client_secret = app.config.get("GOOGLE_CLIENT_SECRET", "")
    linkedin_client_id     = app.config.get("LINKEDIN_CLIENT_ID", "")
    linkedin_client_secret = app.config.get("LINKEDIN_CLIENT_SECRET", "")

    if google_client_id and google_client_secret:
        oauth.register(
            name="google",
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        app.logger.info("Google OAuth client registered.")
    else:
        app.logger.warning(
            "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set — Google login disabled."
        )

    if linkedin_client_id and linkedin_client_secret:
        oauth.register(
            name="linkedin",
            client_id=linkedin_client_id,
            client_secret=linkedin_client_secret,
            access_token_url="https://www.linkedin.com/oauth/v2/accessToken",
            authorize_url="https://www.linkedin.com/oauth/v2/authorization",
            api_base_url="https://api.linkedin.com/",
            client_kwargs={"scope": "r_liteprofile r_emailaddress"},
        )


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app.logger.setLevel(logging.INFO)

    db.init_app(app)
    oauth.init_app(app)
    migrate = Migrate(app, db)


    CORS(
        app,
        supports_credentials=True,
        resources={r"/api/*": {"origins": [app.config["FRONTEND_URL"]]}},
    )

    _register_oauth_clients(app)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.errorhandler(OAuthError)
    def handle_oauth_error(error):
        app.logger.exception("OAuth error", exc_info=error)
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        app.logger.exception("Database error: %s", error)
        db.session.rollback()
        return jsonify({"error": "Database operation failed"}), 500

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(Exception)
    def handle_server_error(error):
        # Always print the full traceback so it appears in the terminal
        import traceback as _tb
        _tb.print_exc()
        app.logger.exception("Unhandled error: %s", error)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"error": "Internal server error", "detail": str(error)}), 500

    with app.app_context():
        db.create_all()
        Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    # Start background job scraper (runs every 10 min, safe to call multiple times)
    start_scraper(app)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
