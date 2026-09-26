"""Offline Railway configuration/ingress tests; sockets are blocked by conftest."""
import runpy

import pytest
from bs4 import BeautifulSoup
from flask import request, url_for

from app import create_app
from app.extensions import db, limiter
from app.proxy import RailwayProxy


def railway_app(monkeypatch, **environment):
    values = {
        "FLASK_ENV": "production", "FLASK_SKIP_DOTENV": "1",
        "SECRET_KEY": "synthetic-railway-test-key-at-least-32-characters",
        "DATABASE_URL": "postgresql://test:test@postgres.railway.internal:5432/railway?sslmode=require",
        "REDIS_URL": "redis://default:synthetic@redis.railway.internal:6379/0",
        "BASE_URL": "https://stage.example.test",
        "TRUSTED_HOSTS": "stage.example.test,healthcheck.railway.app",
        **environment,
    }
    monkeypatch.delenv("RATELIMIT_STORAGE_URI", raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return create_app()


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_railway_database_driver_and_ssl_query(monkeypatch, scheme):
    app = railway_app(monkeypatch, DATABASE_URL=f"{scheme}://test:test@postgres.railway.internal:5432/railway?sslmode=require")
    with app.app_context():
        assert db.engine.url.drivername == "postgresql+psycopg"
        assert db.engine.url.query["sslmode"] == "require"
        assert db.engine.dialect.name == "postgresql"
        assert limiter.storage.__class__.__name__ == "RedisStorage"
    assert not app.config["RATELIMIT_IN_MEMORY_FALLBACK_ENABLED"]
    assert not app.config["RATELIMIT_SWALLOW_ERRORS"]


def test_redis_override_precedence(monkeypatch):
    app = railway_app(monkeypatch, RATELIMIT_STORAGE_URI="rediss://synthetic@override.example.test:6379/1")
    assert app.config["RATELIMIT_STORAGE_URI"].startswith("rediss://synthetic@override")


@pytest.mark.parametrize("redis_url", ["", "memory://", "http://invalid.example.test"])
def test_production_refuses_missing_or_unsafe_redis(monkeypatch, redis_url):
    with pytest.raises(ValueError, match="shared persistent"):
        railway_app(monkeypatch, REDIS_URL=redis_url)


def test_health_without_dependencies_or_rate_limits(monkeypatch):
    app = railway_app(monkeypatch)
    def forbidden(*args, **kwargs):
        raise AssertionError("Health must not access a dependency")
    with app.app_context():
        monkeypatch.setattr(db.engine, "connect", forbidden)
        monkeypatch.setattr(limiter.storage, "incr", forbidden)
    client = app.test_client()
    for _ in range(205):
        response = client.get("/health?lang=el", base_url="http://healthcheck.railway.app")
        assert response.status_code == 200
        assert response.json == {"status": "ok"}
        assert "Set-Cookie" not in response.headers
        assert response.headers["Cache-Control"] == "no-store"
    assert client.head("/health", base_url="https://stage.example.test").status_code == 200
    assert client.get("/health", base_url="https://untrusted.example.test").status_code == 400


def test_proxy_disabled_by_default(monkeypatch):
    app = railway_app(monkeypatch)
    with app.test_request_context("/health", headers={"X-Real-IP": "203.0.113.9", "X-Forwarded-Proto": "https"}):
        assert request.scheme == "http"
    assert not isinstance(app.wsgi_app, RailwayProxy)


def test_proxy_uses_only_documented_edge_headers(monkeypatch):
    app = railway_app(monkeypatch, TRUST_RAILWAY_PROXY="true")
    @app.get("/proxy-test")
    @limiter.exempt
    def probe():
        return {"ip": request.remote_addr, "scheme": request.scheme,
                "host": request.host, "url": url_for("health", _external=True)}
    client = app.test_client()
    headers = {"X-Real-IP": "203.0.113.9", "X-Forwarded-For": "198.51.100.66",
               "X-Forwarded-Proto": "http, https", "X-Forwarded-Host": "attacker.example",
               "X-Forwarded-Port": "444", "X-Forwarded-Prefix": "/spoof"}
    result = client.get("/proxy-test", base_url="http://stage.example.test", headers=headers)
    assert result.json == {"ip": "203.0.113.9", "scheme": "https", "host": "stage.example.test",
                           "url": "https://stage.example.test/health"}
    for invalid in ("garbage", "198.51.100.1, 203.0.113.9", ""):
        headers["X-Real-IP"] = invalid
        result = client.get("/proxy-test", base_url="http://stage.example.test", headers=headers)
        assert result.json["ip"] == "127.0.0.1"


def test_forwarded_https_csrf_and_secure_cookie(app, lead_data):
    app.wsgi_app = RailwayProxy(app.wsgi_app)
    app.config.update(WTF_CSRF_ENABLED=True, SESSION_COOKIE_SECURE=True, RATELIMIT_ENABLED=True)
    client = app.test_client()
    headers = {"X-Forwarded-Proto": "https", "X-Real-IP": "203.0.113.1"}
    response = client.get("/contact", base_url="https://localhost", headers=headers,
                          environ_overrides={"wsgi.url_scheme": "http"})
    cookie = response.headers["Set-Cookie"]
    assert all(value in cookie for value in ("Secure", "HttpOnly", "SameSite=Lax"))
    token = BeautifulSoup(response.data, "html.parser").find("input", attrs={"name": "csrf_token"})["value"]
    headers["Referer"] = "https://localhost/contact"
    response = client.post("/contact", base_url="https://localhost", headers=headers,
                           environ_overrides={"wsgi.url_scheme": "http"},
                           data={**lead_data, "csrf_token": token})
    assert response.status_code == 303


def test_proxy_clients_have_separate_rate_buckets(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (tmp_path / "proxy.db").as_posix(),
                      "RATELIMIT_ENABLED": True, "RATELIMIT_STORAGE_URI": "memory://",
                      "TRUSTED_HOSTS": None})
    app.wsgi_app = RailwayProxy(app.wsgi_app)
    @app.get("/bucket-test")
    @limiter.limit("1 per minute")
    def bucket():
        return "ok"
    client = app.test_client()
    first = {"X-Real-IP": "203.0.113.1", "X-Forwarded-For": "spoofed"}
    second = {"X-Real-IP": "203.0.113.2", "X-Forwarded-For": "spoofed"}
    assert client.get("/bucket-test", headers=first).status_code == 200
    assert client.get("/bucket-test", headers=first).status_code == 429
    assert client.get("/bucket-test", headers=second).status_code == 200


def test_gunicorn_port_and_privacy(monkeypatch):
    monkeypatch.setenv("PORT", "4567")
    config = runpy.run_path("gunicorn.conf.py")
    assert config["bind"] == "0.0.0.0:4567"
    assert config["workers"] == 1 and config["threads"] == 2
    assert config["accesslog"] == config["errorlog"] == "-"
    assert config["access_log_format"] % {"m": "POST", "s": "303", "B": "100", "L": "0.001"} == "POST 303 100 0.001"
