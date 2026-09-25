import smtplib
import socket

import pytest

from app import create_app
from app.extensions import db
from app.models import Admin


@pytest.fixture(autouse=True)
def forbid_real_smtp(monkeypatch):
    import app as application
    monkeypatch.setattr(application, "load_dotenv", lambda *args, **kwargs: None)
    for key in ("DATABASE_URL", "FLASK_DEBUG", "TRUSTED_HOSTS", "MAIL_APP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {"SECRET_KEY": "isolated-test-key-not-for-production", "FLASK_ENV": "development",
                       "MAIL_ENABLED": "false", "MAIL_USE_TLS": "true", "MAIL_PORT": "587",
                       "MAIL_ADDRESS": "xentesvasilis@gmail.com", "CALENDLY_SCHEDULING_URL": "",
                       "BASE_URL": "http://localhost", "RATELIMIT_STORAGE_URI": "memory://"}.items():
        monkeypatch.setenv(key, value)
    def forbidden(*args, **kwargs):
        raise AssertionError("Tests must never open real SMTP connections")
    monkeypatch.setattr(smtplib, "SMTP", forbidden)
    monkeypatch.setattr(smtplib, "SMTP_SSL", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key-not-for-deployment",
                      "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (tmp_path / "test.db").as_posix(),
                      "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False,
                      "MAIL_ENABLED": False, "PRODUCTION": False,
                      "SESSION_COOKIE_SECURE": False, "CALENDLY_SCHEDULING_URL": "",
                      "BASE_URL": "http://localhost", "TRUSTED_HOSTS": None})
    with app.app_context():
        db.create_all()
        admin = Admin(username="tester")
        admin.set_password("test-password-only")
        db.session.add(admin)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def lead_data():
    return dict(name="Test Person", email="prospect@example.com", phone="+30 2100000000",
                company="Example Practice", industry="healthcare", requirements=["website", "booking"],
                budget="1000-2000", description="We need a website and online appointment booking.",
                timeframe="month", privacy_accept="y")


@pytest.fixture
def admin_client(client):
    response = client.post("/admin/login", data={"username": "tester", "password": "test-password-only"})
    assert response.status_code == 303
    return client
