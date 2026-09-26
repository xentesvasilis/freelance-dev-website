from bs4 import BeautifulSoup
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import MagicMock

from app import mail
from app.extensions import db
from app.models import Lead


def make_failed_lead(app, status="failed"):
    with app.app_context():
        lead = Lead(name="Retry Client", email="retry@example.com", industry="healthcare", requirements_json=["website"],
                    budget_range="1000-2000", description="Existing stored lead that must not change.",
                    timeframe="month", language="en", email_status=status)
        db.session.add(lead)
        db.session.commit()
        return lead.public_id


def retry_token(response):
    return BeautifulSoup(response.data, "html.parser").find("input", attrs={"name": "retry_key"})["value"]


def test_retry_requires_admin_post_and_csrf(client, app):
    public_id = make_failed_lead(app)
    path = f"/admin/leads/{public_id}/retry-email"
    assert client.get(path).status_code == 405
    assert client.post(path, data={}).status_code == 302
    admin = app.test_client()
    assert admin.post("/admin/login", data={"username": "tester", "password": "test-password-only"}).status_code == 303
    app.config["WTF_CSRF_ENABLED"] = True
    response = admin.get(f"/admin/leads/{public_id}")
    token = retry_token(response)
    assert admin.post(path, data={"retry_key": token}).status_code == 400
    assert admin.post(path, data={"retry_key": token, "csrf_token": "invalid"}).status_code == 400
    with app.app_context():
        assert db.session.scalar(db.select(Lead.email_status).where(Lead.public_id == public_id)) == "failed"


def test_failed_lead_retry_success_only_changes_notification_status(app, admin_client, monkeypatch):
    public_id = make_failed_lead(app)
    before = admin_client.get(f"/admin/leads/{public_id}")
    token = retry_token(before)
    send = MagicMock(return_value="sent")
    monkeypatch.setattr(mail, "notify_lead", send)
    with app.app_context():
        before_row = dict(db.session.execute(db.select(Lead.__table__).where(Lead.public_id == public_id)).mappings().one())
    path = f"/admin/leads/{public_id}/retry-email"
    first = admin_client.post(path, data={"retry_key": token})
    second = admin_client.post(path, data={"retry_key": token})
    assert first.status_code == second.status_code == 303
    send.assert_called_once()
    assert send.call_args.kwargs["idempotency_key"] == token
    detail = admin_client.get(f"/admin/leads/{public_id}")
    assert b"Sent" in detail.data and b"Retry notification" not in detail.data
    with app.app_context():
        after = dict(db.session.execute(db.select(Lead.__table__).where(Lead.public_id == public_id)).mappings().one())
    assert before_row["email_status"] == "failed" and after["email_status"] == "sent"
    before_row.pop("email_status")
    after.pop("email_status")
    assert before_row == after


def test_failed_retry_stays_failed_and_does_not_log_message(app, admin_client, monkeypatch, caplog):
    public_id = make_failed_lead(app)
    monkeypatch.setattr(mail, "notify_lead", MagicMock(side_effect=mail.MailDeliveryError("network")))
    detail = admin_client.get(f"/admin/leads/{public_id}")
    response = admin_client.post(f"/admin/leads/{public_id}/retry-email", data={"retry_key": retry_token(detail)})
    assert response.status_code == 303
    with app.app_context():
        lead = db.session.scalar(db.select(Lead).where(Lead.public_id == public_id))
        assert lead.email_status == "failed" and lead.description == "Existing stored lead that must not change."
    assert "reason=network" in caplog.text and lead.email not in caplog.text and lead.description not in caplog.text
    assert b"Retry notification" in admin_client.get(response.headers["Location"]).data


def test_sent_lead_cannot_be_retried_even_with_direct_post(app, admin_client, monkeypatch):
    public_id = make_failed_lead(app, status="sent")
    send = MagicMock()
    monkeypatch.setattr(mail, "notify_lead", send)
    detail = admin_client.get(f"/admin/leads/{public_id}")
    assert b"Retry notification" not in detail.data
    from app.admin import _new_retry_key
    with app.app_context():
        key = _new_retry_key(public_id)
    response = admin_client.post(f"/admin/leads/{public_id}/retry-email", data={"retry_key": key})
    assert response.status_code == 303
    send.assert_not_called()


def test_retry_token_cannot_be_reused_for_another_lead(app, admin_client, monkeypatch):
    first = make_failed_lead(app)
    second = make_failed_lead(app)
    token = retry_token(admin_client.get(f"/admin/leads/{first}"))
    send = MagicMock()
    monkeypatch.setattr(mail, "notify_lead", send)
    assert admin_client.post(f"/admin/leads/{second}/retry-email", data={"retry_key": token}).status_code == 400
    send.assert_not_called()


def test_retry_when_disabled_preserves_disabled_state(app, admin_client, monkeypatch):
    public_id = make_failed_lead(app, status="disabled")
    app.config["MAIL_ENABLED"] = False
    send = MagicMock(wraps=mail.notify_lead)
    monkeypatch.setattr(mail, "notify_lead", send)
    detail = admin_client.get(f"/admin/leads/{public_id}")
    response = admin_client.post(f"/admin/leads/{public_id}/retry-email", data={"retry_key": retry_token(detail)})
    assert response.status_code == 303
    with app.app_context():
        assert db.session.scalar(db.select(Lead.email_status).where(Lead.public_id == public_id)) == "disabled"
