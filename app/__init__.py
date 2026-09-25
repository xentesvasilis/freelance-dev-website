import os
import secrets
import logging
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, g, render_template, request, session
from flask_wtf.csrf import CSRFError
from sqlalchemy.engine import make_url
from email_validator import validate_email, EmailNotValidError

from .extensions import csrf, db, limiter, migrate

ROOT = Path(__file__).resolve().parent.parent


class ProductionFlask(Flask):
    @property
    def debug(self):
        return False if self.config.get("PRODUCTION") else self.config["DEBUG"]

    @debug.setter
    def debug(self, value):
        if value and self.config.get("PRODUCTION"):
            raise ValueError("Debug is prohibited in production")
        self.config["DEBUG"] = value

    def log_exception(self, exc_info):
        if self.config.get("PRODUCTION"):
            # Exception messages/SQL driver details can contain submitted data.
            self.logger.error("Unhandled application exception; type=%s endpoint=%s",
                              exc_info[0].__name__, request.endpoint)
        else:
            super().log_exception(exc_info)


def env_bool(name, default):
    value = os.getenv(name, default).lower()
    if value not in ("true", "false"):
        raise ValueError(f"{name} must be true or false")
    return value == "true"


def create_app(test_config=None):
    if os.getenv("FLASK_ENV") != "production" and not (test_config or {}).get("TESTING"):
        load_dotenv(ROOT / ".env")
    app = ProductionFlask(__name__, instance_path=str(ROOT / "instance"))
    mode = os.getenv("FLASK_ENV", "development")
    if mode not in ("development", "production"):
        raise ValueError("FLASK_ENV must be development or production")
    production = mode == "production"
    database = os.getenv("DATABASE_URL") or "sqlite:///site.db"
    if database.startswith("postgres://"):
        database = database.replace("postgres://", "postgresql+psycopg://", 1)
    elif database.startswith("postgresql://"):
        database = database.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=database, SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"hide_parameters": True, "pool_pre_ping": True},
        BASE_URL=os.getenv("BASE_URL", "http://127.0.0.1:5000").rstrip("/"),
        PRODUCTION=production, DEBUG=False, SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=production,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2), MAX_CONTENT_LENGTH=64 * 1024,
        WTF_CSRF_TIME_LIMIT=7200,
        MAIL_ENABLED=env_bool("MAIL_ENABLED", "false"),
        MAIL_HOST=os.getenv("MAIL_HOST", "smtp.gmail.com"), MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
        MAIL_USE_TLS=env_bool("MAIL_USE_TLS", "true"),
        MAIL_ADDRESS=os.getenv("MAIL_ADDRESS", "xentesvasilis@gmail.com"),
        MAIL_APP_PASSWORD=os.getenv("MAIL_APP_PASSWORD", ""),
        CALENDLY_SCHEDULING_URL=os.getenv("CALENDLY_SCHEDULING_URL", ""),
        RATELIMIT_STORAGE_URI=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        TRUSTED_HOSTS=[h.strip() for h in os.getenv("TRUSTED_HOSTS", "").split(",") if h.strip()] or None,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        raise ValueError("SECRET_KEY must be supplied through the environment")
    base = urlsplit(app.config["BASE_URL"])
    if base.scheme not in ("http", "https") or not base.hostname or base.path not in ("", "/") or base.query or base.fragment or base.username or any(c.isspace() for c in base.netloc):
        raise ValueError("BASE_URL must be an HTTP(S) origin")
    calendly = urlsplit(app.config["CALENDLY_SCHEDULING_URL"])
    if calendly.geturl() and (calendly.scheme != "https" or calendly.hostname != "calendly.com" or calendly.username or calendly.port not in (None, 443)):
        raise ValueError("CALENDLY_SCHEDULING_URL must use https://calendly.com")
    if app.config["PRODUCTION"]:
        if os.getenv("FLASK_DEBUG", "0").lower() not in ("0", "false", "") or app.config["DEBUG"]:
            raise ValueError("Debug is prohibited in production")
        app.config.update(DEBUG=False, SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True,
                          SESSION_COOKIE_SAMESITE="Lax", WTF_CSRF_ENABLED=True,
                          RATELIMIT_ENABLED=True, PROPAGATE_EXCEPTIONS=False)
        if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
            raise ValueError("Production requires a strong SECRET_KEY of at least 32 characters")
        if base.scheme != "https" or not app.config["TRUSTED_HOSTS"]:
            raise ValueError("Production requires HTTPS BASE_URL and TRUSTED_HOSTS")
        if urlsplit(app.config["RATELIMIT_STORAGE_URI"]).scheme not in ("redis", "rediss"):
            raise ValueError("Production requires shared persistent rate-limit storage")
        if not os.getenv("DATABASE_URL"):
            raise ValueError("Production requires DATABASE_URL")
        if make_url(app.config["SQLALCHEMY_DATABASE_URI"]).drivername != "postgresql+psycopg":
            raise ValueError("Production DATABASE_URL must use PostgreSQL with psycopg")
        if base.hostname in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Production BASE_URL must use the public hostname")
        if not any(base.hostname == h or (h.startswith(".") and base.hostname.endswith(h)) for h in app.config["TRUSTED_HOSTS"]):
            raise ValueError("BASE_URL hostname must be in TRUSTED_HOSTS")
        app.config["SQLALCHEMY_ENGINE_OPTIONS"].update(connect_args={"connect_timeout": 10}, pool_recycle=300)
        app.logger.setLevel(logging.INFO)
    if app.config["MAIL_ENABLED"]:
        try:
            validate_email(app.config["MAIL_ADDRESS"], check_deliverability=False)
        except EmailNotValidError:
            raise ValueError("MAIL_ADDRESS must be a valid email address") from None
        if not app.config["MAIL_APP_PASSWORD"] or not app.config["MAIL_HOST"]:
            raise ValueError("Enabled mail requires MAIL_HOST and MAIL_APP_PASSWORD")
        if not 1 <= app.config["MAIL_PORT"] <= 65535 or (not app.config["MAIL_USE_TLS"] and app.config["MAIL_PORT"] != 465):
            raise ValueError("Mail requires a valid port and encrypted SMTP")
    Path(app.instance_path).mkdir(exist_ok=True)

    @app.before_request
    def language():
        requested = request.args.get("lang")
        if requested in ("el", "en"):
            session["language"] = requested
        g.lang = session.get("language", "en")
        g.csp_nonce = secrets.token_urlsafe(18)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    csrf.init_app(app)
    limiter.init_app(app)

    from .public import public
    from .admin import admin
    from .cli import register_cli
    from .content import CONTENT, PACKAGES, tr
    app.register_blueprint(public)
    app.register_blueprint(admin)
    register_cli(app)

    @app.context_processor
    def shared():
        lang = getattr(g, "lang", "en")
        return dict(t=tr, lang=lang, content=CONTENT, packages=PACKAGES,
                    choose_language="language" not in session and request.blueprint == "public",
                    canonical=app.config["BASE_URL"] + request.path + "?lang=" + lang,
                    base_url=app.config["BASE_URL"])

    @app.after_request
    def headers(response):
        nonce = getattr(g, "csp_nonce", "")
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; script-src 'self' 'nonce-{nonce}' https://assets.calendly.com; "
            "style-src 'self' 'unsafe-inline' https://assets.calendly.com; "
            "img-src 'self' data:; font-src 'self'; frame-src https://calendly.com; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        if request.blueprint == "admin" or request.path == "/book-call":
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template("error.html", code=400, message=tr("csrf_error")), 400

    for code in (400, 403, 404, 413, 429, 500, 503):
        def handler(error, code=code):
            db.session.rollback()
            return render_template("error.html", code=code, message=tr("error_" + str(code))), code
        app.register_error_handler(code, handler)
    return app
