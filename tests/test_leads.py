import json
import smtplib
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app import mail
from app.extensions import db
from app.models import Lead


def saved_lead(app):
    with app.app_context():
        return db.session.scalar(db.select(Lead))


@pytest.mark.parametrize("field,value", [("name", ""), ("email", "not-an-email"), ("industry", "invalid"), ("requirements", ["invalid"]), ("requirements", []), ("budget", "invalid"), ("description", "short"), ("timeframe", "invalid"), ("privacy_accept", ""), ("name", "x" * 121), ("company", "x" * 161), ("phone", "x" * 41), ("description", "x" * 4001), ("name", "Test\r\nBcc: other@example.com")])
def test_contact_validation(app, client, lead_data, field, value, monkeypatch):
    notification = MagicMock()
    monkeypatch.setattr(mail, "notify_lead", notification)
    lead_data[field] = value
    response = client.post("/contact?lang=en", data=lead_data)
    assert response.status_code == 422
    assert b"Please review the highlighted fields" in response.data
    assert saved_lead(app) is None
    notification.assert_not_called()


def test_lead_committed_before_notification(app, client, lead_data, monkeypatch):
    def notify(lead, **kwargs):
        # Independent DB connection proves this isn't merely a pending ORM flush.
        engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        try:
            with engine.connect() as connection:
                row = connection.execute(text("SELECT email, email_status FROM lead WHERE public_id=:id"), {"id": lead.public_id}).one()
                assert row.email == lead_data["email"]
                assert row.email_status == "pending"
        finally:
            engine.dispose()
        return "sent"
    notification = MagicMock(side_effect=notify)
    monkeypatch.setattr(mail, "notify_lead", notification)
    response = client.post("/contact?lang=el", data=lead_data)
    assert response.status_code == 303
    assert response.location == "/book-call"
    notification.assert_called_once()
    lead = saved_lead(app)
    assert lead.email_status == "sent"
    assert lead.language == "el"
    assert lead.status == "new"
    assert len(lead.public_id) >= 40 and not lead.public_id.isdigit()
    assert lead.privacy_accepted_at
    with client.session_transaction() as session:
        assert session["booking_lead"] == lead.public_id
        assert "name" not in session and "email" not in session
    assert b'prospect@example.com' not in response.data


def test_smtp_failure_preserves_lead(app, client, lead_data, monkeypatch, caplog):
    monkeypatch.setattr(mail, "notify_lead", MagicMock(side_effect=smtplib.SMTPException("private-provider-details")))
    response = client.post("/contact?lang=en", data=lead_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"your brief has been saved" in response.data
    assert saved_lead(app).email_status == "failed"
    assert lead_data["email"] not in caplog.text
    assert "private-provider-details" not in caplog.text


def test_disabled_mail_still_saves(app, client, lead_data):
    assert client.post("/contact", data=lead_data).status_code == 303
    assert saved_lead(app).email_status == "disabled"


def test_database_failure_does_not_send(app, client, lead_data, monkeypatch):
    notification = MagicMock()
    monkeypatch.setattr(mail, "notify_lead", notification)
    monkeypatch.setattr(db.session, "commit", MagicMock(side_effect=SQLAlchemyError("private-db-details")))
    response = client.post("/contact", data=lead_data)
    assert response.status_code == 503
    assert b"private-db-details" not in response.data
    notification.assert_not_called()
    assert saved_lead(app) is None


def test_notification_state_failure_keeps_success(app, client, lead_data, monkeypatch):
    original = db.session.commit
    calls = 0
    def commit():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise SQLAlchemyError("notification status write failed")
        return original()
    monkeypatch.setattr(db.session, "commit", commit)
    response = client.post("/contact?lang=en", data=lead_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"your brief has been saved" in response.data
    assert saved_lead(app).email_status == "pending"


def test_mocked_smtp_success_and_html_escaping(app, client, lead_data, monkeypatch):
    connection = MagicMock()
    smtp = connection.__enter__.return_value
    factory = MagicMock(return_value=connection)
    monkeypatch.setattr(smtplib, "SMTP", factory)
    app.config.update(MAIL_ENABLED=True, MAIL_PROVIDER="smtp", MAIL_APP_PASSWORD="mock-only", MAIL_USE_TLS=True, MAIL_PORT=587)
    lead_data["description"] = '<script>alert("x")</script> & a website request.'
    response = client.post("/contact", data=lead_data)
    assert response.status_code == 303
    assert saved_lead(app).email_status == "sent"
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("xentesvasilis@gmail.com", "mock-only")
    message = smtp.send_message.call_args.args[0]
    assert message["From"] == message["To"] == "xentesvasilis@gmail.com"
    assert message["Subject"] == "New Freelance Project Lead - Test Person"
    html = message.get_body(preferencelist=("html",)).get_content()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    body = message.get_body(preferencelist=("plain",)).get_content()
    for value in [lead_data["email"], lead_data["company"], "Healthcare", "New website", "Booking system", "€1,000–€2,000", "Within 1 month", lead_data["description"]]:
        assert value in body


def test_calendly_direct_prefill_and_expiration(app, client, lead_data):
    assert b"Online scheduling is being prepared" in client.get("/book-call?lang=en").data
    app.config["CALENDLY_SCHEDULING_URL"] = "https://calendly.com/example/discovery"
    direct = BeautifulSoup(client.get("/book-call").data, "html.parser")
    assert json.loads(direct.find(id="calendar-config").string)["prefill"] == {}
    assert not direct.select('script[src*="calendly"]')
    assert not direct.find("iframe")
    client.post("/contact", data=lead_data)
    response = client.get("/book-call")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    soup = BeautifulSoup(response.data, "html.parser")
    config = json.loads(soup.find(id="calendar-config").string)
    assert config["prefill"] == {"name": lead_data["name"], "email": lead_data["email"]}
    # A second visitor cannot retrieve another visitor's details.
    other = BeautifulSoup(app.test_client().get("/book-call").data, "html.parser")
    assert json.loads(other.find(id="calendar-config").string)["prefill"] == {}
    with client.session_transaction() as session:
        session["booking_until"] = 1
    expired = BeautifulSoup(client.get("/book-call").data, "html.parser")
    assert json.loads(expired.find(id="calendar-config").string)["prefill"] == {}


def test_optional_fields_and_public_no_sequential_ids(app, client, lead_data):
    lead_data.update(phone="", company="")
    response = client.post("/contact", data=lead_data)
    assert response.status_code == 303
    lead = saved_lead(app)
    assert client.get("/leads/" + str(lead.id)).status_code == 404
    assert client.get("/leads/" + lead.public_id).status_code == 404


def test_greek_validation(client):
    response = client.post("/contact?lang=el", data={})
    assert response.status_code == 422
    assert 'Παρακαλώ συμπληρώστε'.encode() in response.data
