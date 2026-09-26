"""Opt-in live checks against ONLY the disposable local Compose services.

No real .env is loaded. No Gmail/Calendly calls. Credentials are never printed.
Each run creates and drops its own staging_verify_* PostgreSQL database.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import smtplib
import socket
import sys
import threading
from http.client import HTTPConnection
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STAGING_ENV = ROOT / ".env.local-staging"


def prepare():
    if STAGING_ENV.exists():
        print("Existing local staging environment retained; no values displayed.")
        return
    with STAGING_ENV.open("x", encoding="utf-8") as stream:
        stream.write("# Disposable local staging only. Never production.\n")
        stream.write("LOCAL_STAGING_DB_PASSWORD=" + secrets.token_hex(32) + "\n")
    print("Created ignored .env.local-staging with a fresh local-only credential.")


def verify():
    if not shutil.which("docker"):
        print("BLOCKED: Docker CLI unavailable. Install/start Docker Desktop with Compose V2 and Linux containers.")
        return 2
    if not STAGING_ENV.exists():
        print("BLOCKED: Run this script with --prepare, then start the local Compose services.")
        return 2
    from dotenv import dotenv_values
    from bs4 import BeautifulSoup
    import psycopg
    from psycopg import sql
    from redis import Redis
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import IntegrityError

    password = dotenv_values(STAGING_ENV).get("LOCAL_STAGING_DB_PASSWORD", "")
    if len(password) != 64 or any(c not in "0123456789abcdef" for c in password):
        print("BLOCKED: Invalid generated local staging credential format.")
        return 2
    run_id = secrets.token_hex(8)
    database = "staging_verify_" + run_id
    prefix = "staging_verify_" + run_id
    environment = {
        "FLASK_ENV": "production", "FLASK_DEBUG": "0", "FLASK_SKIP_DOTENV": "1",
        "SECRET_KEY": secrets.token_hex(32),
        "DATABASE_URL": f"postgresql+psycopg://local_staging:{password}@127.0.0.1:55432/{database}",
        "RATELIMIT_STORAGE_URI": "redis://127.0.0.1:56379/15",
        "BASE_URL": "https://staging.example.test", "TRUSTED_HOSTS": "staging.example.test",
        "MAIL_ENABLED": "false", "MAIL_HOST": "smtp.invalid", "MAIL_PORT": "587",
        "MAIL_USE_TLS": "true", "MAIL_ADDRESS": "staging@example.com", "MAIL_APP_PASSWORD": "",
        "CALENDLY_SCHEDULING_URL": "",
    }
    # Windows cryptographic providers need SystemRoot for libpq SCRAM nonces.
    # Keep only this OS setting while isolating all application configuration.
    if "SYSTEMROOT" in os.environ:
        environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    original_connect = socket.socket.connect
    allowed_targets = {("127.0.0.1", 55432), ("127.0.0.1", 56379)}
    def local_connect(sock, address):
        if not isinstance(address, tuple) or address[:2] not in allowed_targets:
            raise RuntimeError("Non-staging network connection blocked")
        return original_connect(sock, address)
    def no_smtp(*args, **kwargs):
        raise RuntimeError("SMTP prohibited in staging automation")

    checks = []
    connection = None
    created = False
    application = None
    redis = Redis(host="127.0.0.1", port=56379, db=15, socket_timeout=3, socket_connect_timeout=3)
    phase = "connectivity"
    outcome = 1
    try:
        with patch.dict(os.environ, environment, clear=True), patch.object(socket.socket, "connect", local_connect), \
                patch.object(smtplib, "SMTP", no_smtp), patch.object(smtplib, "SMTP_SSL", no_smtp):
            connection = psycopg.connect(host="127.0.0.1", port=55432, user="local_staging",
                                         password=password, dbname="local_staging", connect_timeout=5, autocommit=True)
            assert redis.ping()
            checks.append("PostgreSQL and Redis connectivity")
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
            created = True
            from app import create_app
            from app.extensions import db, limiter
            from app.models import Admin, Lead, PortfolioProject
            application = create_app({"RATELIMIT_KEY_PREFIX": prefix,
                                      "RATELIMIT_STORAGE_OPTIONS": {"socket_timeout": 3, "socket_connect_timeout": 3}})
            assert application.config["PRODUCTION"] and not application.debug
            assert not application.config["RATELIMIT_IN_MEMORY_FALLBACK_ENABLED"]
            assert not application.config["RATELIMIT_SWALLOW_ERRORS"]
            phase = "migrations"
            runner = application.test_cli_runner()
            for args in (["db", "upgrade"], ["db", "current"], ["db", "check"]):
                result = runner.invoke(args=args)
                assert result.exit_code == 0, "Migration command failed"
            with application.app_context():
                assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "c8a4e291d630"
                inspector = inspect(db.engine)
                assert {"admin", "lead", "portfolio_project", "project_case", "alembic_version"} <= set(inspector.get_table_names())
                assert {"ix_lead_status", "ix_lead_created_at"} <= {v["name"] for v in inspector.get_indexes("lead")}
                assert "valid_lead_status" in {v["name"] for v in inspector.get_check_constraints("lead")}
                assert any(v["column_names"] == ["public_id"] for v in inspector.get_unique_constraints("lead"))
            checks.append("Fresh PostgreSQL migrations, current revision, schema drift, indexes and constraints")
            phase = "admin"
            admin_password = secrets.token_urlsafe(32)
            result = runner.invoke(args=["create-admin"], input=f"owner@example.com\n{admin_password}\n{admin_password}\n")
            assert result.exit_code == 0 and admin_password not in result.output
            assert runner.invoke(args=["create-admin"], input="owner@example.com\n").exit_code != 0
            assert runner.invoke(args=["seed-dev"]).exit_code != 0
            client = application.test_client()
            origin = environment["BASE_URL"]
            def get(path):
                return client.get(path, base_url=origin)
            def csrf(response):
                return BeautifulSoup(response.data, "html.parser").find("input", attrs={"name": "csrf_token"})["value"]
            def post(path, data, token):
                return client.post(path, base_url=origin, headers={"Referer": origin + "/"},
                                   data={**data, "csrf_token": token})
            login = get("/admin/login")
            assert post("/admin/login", {"username": "owner@example.com", "password": admin_password}, csrf(login)).status_code == 303
            assert get("/admin").status_code == 200
            checks.append("Interactive admin creation, duplicate rejection, hashed login and seed-dev refusal")
            phase = "lead and portfolio CRUD"
            for language in ("el", "en"):
                response = get("/?lang=" + language)
                assert response.status_code == 200
                assert "Secure" in response.headers.get("Set-Cookie", "")
            data = {"name": "Δοκιμή English", "email": "prospect@example.com", "phone": "", "company": "Εταιρεία",
                    "industry": "healthcare", "requirements": ["website"], "budget": "1000-2000",
                    "description": "Ελληνικά και English staging enquiry.", "timeframe": "month", "privacy_accept": "y"}
            assert post("/contact?lang=el", data, csrf(get("/contact"))).status_code == 303
            with application.app_context():
                lead = db.session.scalar(db.select(Lead))
                assert lead.name == data["name"] and lead.description == data["description"] and lead.email_status == "disabled"
                public_id = lead.public_id
            detail = "/admin/leads/" + public_id
            assert post(detail + "/status", {"status": "qualified"}, csrf(get(detail))).status_code == 303
            assert post(detail + "/notes", {"notes": "Σημειώσεις / English"}, csrf(get(detail))).status_code == 303
            with application.app_context():
                lead = db.session.scalar(db.select(Lead))
                assert lead.status == "qualified" and lead.notes == "Σημειώσεις / English"
                lead.status = "invalid"
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                else:
                    raise AssertionError("Status constraint not enforced")
                assert db.session.scalar(db.select(Lead)).status == "qualified"
                lead.description = "rollback-test"
                db.session.flush()
                db.session.rollback()
                assert lead.description == data["description"]
                project = PortfolioProject(slug=prefix, title={"el": "Έργο", "en": "Project"},
                    short_description={"el": "Δοκιμή", "en": "Test"}, description={"el": "Περιγραφή", "en": "Description"},
                    industry="staging", technologies=["Flask"], features=["Unicode"], published=True)
                db.session.add(project)
                db.session.commit()
                db.session.expire_all()
                assert project.title == {"el": "Έργο", "en": "Project"}
                project.title = {"el": "Νέο έργο", "en": "Updated project"}
                db.session.commit()
                assert db.session.get(PortfolioProject, project.id).title["el"] == "Νέο έργο"
                db.session.delete(project)
                secondary = Admin(username="delete-me@example.com")
                secondary.set_password(secrets.token_urlsafe(32))
                db.session.add(secondary)
                db.session.commit()
                secondary.username = "updated@example.com"
                db.session.commit()
                assert db.session.get(Admin, secondary.id).username == "updated@example.com"
                db.session.delete(secondary)
                db.session.commit()
                duplicate = Admin(username="owner@example.com")
                duplicate.set_password(secrets.token_urlsafe(32))
                db.session.add(duplicate)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                else:
                    raise AssertionError("Admin uniqueness not enforced")
            checks.append("Admin CRUD, Lead create/read/update, Portfolio CRUD, Unicode, transactions and constraint rollback")
            phase = "Redis rate limits"
            csrf_token = csrf(get("/admin/login"))
            statuses = [post("/admin/login", {"username": "unknown", "password": "wrong"}, csrf_token).status_code for _ in range(5)]
            assert statuses[:4] == [200] * 4 and statuses[4] == 429
            assert any(redis.scan_iter(match="*" + prefix + "*"))
            with application.app_context():
                assert limiter.storage.__class__.__name__ == "RedisStorage"
                # Inject failure without stopping/shared service mutation; must fail closed.
                with patch.object(limiter.storage, "incr", side_effect=ConnectionError("simulated local Redis outage")):
                    assert get("/services").status_code == 500
            checks.append("Real Redis counters and 429; simulated outage refuses in-memory fallback")
            phase = "SEO and errors"
            for path in ("/sitemap.xml", "/robots.txt"):
                response = get(path)
                assert response.status_code == 200 and origin in response.text
            assert get("/not-a-route").status_code == 404
            checks.append("Production-origin sitemap/robots and custom 404")
            phase = "temporary HTTP application startup"
            from werkzeug.serving import make_server
            server = make_server("127.0.0.1", 0, application)
            target = ("127.0.0.1", server.server_port)
            allowed_targets.add(target)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            http = HTTPConnection(*target, timeout=5)
            worker.start()
            try:
                for path in ("/?lang=el", "/?lang=en", "/admin/login"):
                    http.request("GET", path, headers={"Host": "staging.example.test"})
                    response = http.getresponse()
                    assert response.status == 200
                    assert response.read()
            finally:
                http.close()
                server.shutdown()
                worker.join(timeout=5)
                server.server_close()
                allowed_targets.remove(target)
            assert not worker.is_alive()
            checks.append("Temporary loopback HTTP startup, Greek/English pages and admin login; server stopped")
            outcome = 0
    except Exception as exc:
        # Never print exception messages, URLs, CLI output, records or credentials.
        print(f"FAILED: {phase} ({type(exc).__name__}); details suppressed to protect credentials.")
    finally:
        if application is not None:
            with application.app_context():
                db.session.remove()
                db.engine.dispose()
        if created and connection is not None:
            try:
                connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
            except Exception:
                outcome = 1
                print("Cleanup incomplete: a staging_verify_* database remains in the disposable local container.")
        if connection is not None:
            connection.close()
        try:
            for key in redis.scan_iter(match="*" + prefix + "*"):
                redis.delete(key)
        except Exception:
            if outcome == 0:
                outcome = 1
                print("Cleanup incomplete: local staging Redis keys remain.")
        redis.close()
    for check in checks:
        print("PASS: " + check)
    report = ROOT / ".test-tmp" / "staging-live-result.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps({"passed": outcome == 0, "checks": checks}, indent=2), encoding="utf-8")
    return outcome


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        raise SystemExit("Run from the project root.")
    if args.prepare:
        prepare()
    else:
        raise SystemExit(verify())
