import json
import socket

import pytest
from bs4 import BeautifulSoup
from flask import abort

from app import create_app
from app.extensions import db


def production(monkeypatch, **overrides):
    monkeypatch.setenv("DATABASE_URL", "postgresql://audit:audit@localhost/audit")
    return create_app({"PRODUCTION": True, "SECRET_KEY": "test-only-production-key-with-32-characters",
                       "BASE_URL": "https://example.com", "TRUSTED_HOSTS": ["example.com"],
                       "RATELIMIT_STORAGE_URI": "redis://localhost:6379/0", **overrides})


def test_production_config_and_no_import_connections(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No network connections during app creation")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    app = production(monkeypatch)
    assert not app.debug
    with pytest.raises(ValueError, match="Debug"):
        app.debug = True
    for key in ("SESSION_COOKIE_SECURE", "SESSION_COOKIE_HTTPONLY", "WTF_CSRF_ENABLED", "RATELIMIT_ENABLED"):
        assert app.config[key]
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    with app.app_context():
        assert db.engine.dialect.name == "postgresql"
        assert db.engine.pool._pre_ping
    result = app.test_cli_runner().invoke(args=["db", "upgrade", "--sql"])
    assert result.exit_code == 0, result.output
    assert "CREATE TABLE lead" in result.output


def test_debug_environment_rejected(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "1")
    with pytest.raises(ValueError, match="Debug"):
        production(monkeypatch)


def test_missing_environment_secret(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app()


@pytest.mark.parametrize("value", ["sqlite:///site.db", ""])
def test_production_database_required(monkeypatch, value):
    monkeypatch.setenv("DATABASE_URL", value)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_app({"PRODUCTION": True, "BASE_URL": "https://example.com", "TRUSTED_HOSTS": ["example.com"],
                    "RATELIMIT_STORAGE_URI": "redis://localhost/0"})


def test_error_pages_and_safe_logging(app, client, caplog):
    @app.get("/audit-error/<int:code>")
    def fail(code):
        if code == 500:
            raise RuntimeError("PRIVATE_SUBMITTED_CONTENT")
        abort(code)
    app.config.update(PRODUCTION=True, PROPAGATE_EXCEPTIONS=False)
    for code in (403, 404, 500):
        response = client.get(f"/audit-error/{code}")
        assert response.status_code == code
        assert b"PRIVATE_SUBMITTED_CONTENT" not in response.data
    assert "PRIVATE_SUBMITTED_CONTENT" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_production_seo_urls(app, client):
    app.config["BASE_URL"] = "https://example.com"
    for language in ("en", "el"):
        soup = BeautifulSoup(client.get("/services?lang=" + language).data, "html.parser")
        assert soup.find("link", rel="canonical")["href"] == "https://example.com/services?lang=" + language
        assert all(n["href"].startswith("https://example.com/") for n in soup.select("link[hreflang]"))
        assert soup.find("meta", property="og:url")["content"].startswith("https://example.com/")
        assert json.loads(soup.find("script", type="application/ld+json").string)["url"] == "https://example.com"
    for path in ("/robots.txt", "/sitemap.xml"):
        body = client.get(path).text
        assert "https://example.com" in body
        assert "localhost" not in body


def test_route_method_scan(app):
    for rule in app.url_map.iter_rules():
        if rule.endpoint in ("admin.logout", "admin.status", "admin.notes", "public.set_language"):
            assert rule.methods == {"POST", "OPTIONS"}


def test_existing_development_session_rejected(app, client):
    assert app.test_cli_runner().invoke(args=["seed-dev"]).exit_code == 0
    assert client.post("/admin/login", data={"username": "dev-admin", "password": "dev-only-change-before-launch"}).status_code == 303
    app.config["PRODUCTION"] = True
    assert client.get("/admin").status_code == 302
    result = app.test_cli_runner().invoke(args=["create-admin", "--username", "dev-admin", "--password", "long-testing-password"])
    assert result.exit_code != 0
