from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from app import create_app
from app.extensions import db
from app.models import Admin, Lead


def test_public_cannot_access_admin(client):
    for path in ("/admin", "/admin/leads", "/admin/leads/unknown"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.location == "/admin/login"
        assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert b'language-gate' not in client.get("/admin/login").data
    for action in ("status", "notes"):
        assert client.post("/admin/leads/unknown/" + action, data={}).status_code == 302


def test_login_failure_and_logout(app, client):
    for username in ("tester", "unknown", "' OR 1=1 --"):
        response = client.post("/admin/login", data={"username": username, "password": "wrong"})
        assert b"Invalid username or password" in response.data
        assert client.get("/admin").status_code == 302
    client.post("/admin/login", data={"username": "tester", "password": "test-password-only"})
    assert client.get("/admin").status_code == 200
    assert client.get("/admin/logout").status_code == 405
    assert client.post("/admin/logout").status_code == 303
    assert client.get("/admin").status_code == 302
    with app.app_context():
        admin = db.session.scalar(db.select(Admin))
        assert admin.password_hash != "test-password-only"
        assert admin.check_password("test-password-only")


def test_admin_lead_workflow(app, admin_client, lead_data):
    admin_client.post("/contact", data=lead_data)
    with app.app_context():
        public_id = db.session.scalar(db.select(Lead.public_id))
    response = admin_client.get("/admin/leads")
    assert b"Test Person" in response.data
    assert public_id.encode() in response.data
    detail = "/admin/leads/" + public_id
    assert admin_client.get(detail).status_code == 200
    for state in ("contacted", "qualified", "won", "lost", "archived", "new"):
        assert admin_client.post(detail + "/status", data={"status": state}).status_code == 303
        with app.app_context():
            lead = db.session.scalar(db.select(Lead))
            assert lead.status == state
            assert lead.contacted_at is not None
    assert admin_client.post(detail + "/status", data={"status": "invalid"}).status_code == 400
    assert admin_client.get(detail + "/status").status_code == 405
    assert admin_client.get(detail + "/notes").status_code == 405
    assert admin_client.post(detail + "/notes", data={"notes": '<script>alert("x")</script>'}).status_code == 303
    assert b'&lt;script&gt;' in admin_client.get(detail).data
    assert b'<script>alert' not in admin_client.get(detail).data
    assert admin_client.post(detail + "/notes", data={"notes": "x" * 10001}).status_code == 400
    assert admin_client.get("/admin/leads/nonexistent").status_code == 404
    assert b"Total leads" in admin_client.get("/admin").data


def token(response):
    return BeautifulSoup(response.data, "html.parser").find("input", attrs={"name": "csrf_token"})["value"]


def test_csrf_contact_language_login_and_admin(app, client, lead_data):
    app.config["WTF_CSRF_ENABLED"] = True
    for path, data in [("/contact", lead_data), ("/language", {"language": "el"}), ("/admin/login", {"username": "tester", "password": "test-password-only"})]:
        assert client.post(path, data=data).status_code == 400
    csrf = token(client.get("/contact"))
    assert client.post("/contact", data={**lead_data, "csrf_token": csrf}).status_code == 303
    csrf = token(client.get("/admin/login"))
    assert client.post("/admin/login", data={"username": "tester", "password": "test-password-only", "csrf_token": csrf}).status_code == 303
    with app.app_context():
        public_id = db.session.scalar(db.select(Lead.public_id))
    detail = "/admin/leads/" + public_id
    for endpoint, data in [(detail + "/status", {"status": "won"}), (detail + "/notes", {"notes": "test"}), ("/admin/logout", {})]:
        assert client.post(endpoint, data=data).status_code == 400
        assert client.post(endpoint, data={**data, "csrf_token": "invalid"}).status_code == 400
    csrf = token(client.get(detail))
    assert client.post(detail + "/status", data={"status": "won", "csrf_token": csrf}).status_code == 303
    assert client.post(detail + "/notes", data={"notes": "valid notes", "csrf_token": csrf}).status_code == 303
    assert client.post("/admin/logout", data={"csrf_token": csrf}).status_code == 303


def test_revoked_admin_session(app, admin_client):
    with app.app_context():
        db.session.delete(db.session.scalar(db.select(Admin)))
        db.session.commit()
    assert admin_client.get("/admin").status_code == 302


def test_production_refuses_development_admin(app, client):
    assert app.test_cli_runner().invoke(args=["seed-dev"]).exit_code == 0
    app.config["PRODUCTION"] = True
    response = client.post("/admin/login", data={"username": "dev-admin", "password": "dev-only-change-before-launch"})
    assert b"Invalid username or password" in response.data
    assert client.get("/admin").status_code == 302


def test_greek_csrf_error(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post("/contact?lang=el", data={})
    assert response.status_code == 400
    assert 'Η φόρμα έληξε'.encode() in response.data


def test_database_errors_hide_parameters(app):
    with app.app_context():
        assert db.engine.hide_parameters


def test_rate_limits(tmp_path):
    app = create_app({"TESTING": True, "PRODUCTION": False, "SECRET_KEY": "rate-limit-test", "WTF_CSRF_ENABLED": False,
                      "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (tmp_path / "rate.db").as_posix(),
                      "RATELIMIT_ENABLED": True, "RATELIMIT_STORAGE_URI": "memory://", "TRUSTED_HOSTS": None})
    client = app.test_client()
    assert client.post("/contact", data={}).status_code == 422
    assert client.post("/contact", data={}).status_code == 422
    assert client.post("/contact", data={}).status_code == 429
    for _ in range(5):
        assert client.post("/admin/login", data={}).status_code == 200
    assert client.post("/admin/login", data={}).status_code == 429
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.mark.parametrize("url", ["http://calendly.com/example", "https://evil.example/event", "javascript:alert(1)", "https://calendly.com.evil.example/test", "https://user@calendly.com/event"])
def test_invalid_calendly_url(url):
    with pytest.raises(ValueError):
        create_app({"PRODUCTION": False, "CALENDLY_SCHEDULING_URL": url})


def test_production_guards():
    base = {"PRODUCTION": True, "SECRET_KEY": "", "CALENDLY_SCHEDULING_URL": "", "BASE_URL": "http://localhost", "TRUSTED_HOSTS": None, "RATELIMIT_STORAGE_URI": "memory://"}
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app(base)
    base["SECRET_KEY"] = "test-only-long-enough-configuration-value"
    with pytest.raises(ValueError, match="HTTPS"):
        create_app(base)
    base.update(BASE_URL="https://example.com", TRUSTED_HOSTS=["example.com"])
    with pytest.raises(ValueError, match="rate-limit"):
        create_app(base)
