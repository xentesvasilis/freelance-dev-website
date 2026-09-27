import smtplib
from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import resend

from app import create_app
from app import mail
from app.extensions import db
from app.models import Lead


API_KEY = "synthetic-resend-key-never-real"
PRIVATE_BODY = "PRIVATE_LEAD_BODY_MARKER"


def lead_object(**overrides):
    values = dict(name="Test Person", email="prospect@example.com", phone="+30 2100000000",
                           company="Example Practice", industry="healthcare", requirements_json=["website", "booking"],
                           budget_range="1000-2000", timeframe="month", description="Greek Ελληνικά and English project.",
                           )
    values.update(overrides)
    return SimpleNamespace(**values)


def resend_config(app, **overrides):
    values = dict(MAIL_ENABLED=True, MAIL_PROVIDER="resend", RESEND_API_KEY=API_KEY,
                  RESEND_FROM_ADDRESS="Website Leads <onboarding@resend.dev>",
                  MAIL_ADDRESS="owner@example.com")
    values.update(overrides)
    app.config.update(values)


def test_resend_success_content_reply_to_and_from(app, monkeypatch):
    resend_config(app)
    captured = {}
    def accepted(payload, options=None):
        captured.update(payload=payload, options=options, api_key=resend.api_key)
        return {"id": "email_synthetic"}
    monkeypatch.setattr(resend.Emails, "send", accepted)
    with app.app_context():
        result = mail.notify_lead(lead_object(), idempotency_key="signed-test-retry-key")
    body = captured["payload"]
    assert captured["api_key"] == API_KEY and result == "sent"
    assert captured["options"] == {"idempotency_key": "signed-test-retry-key"}
    assert body["from"] == "Website Leads <onboarding@resend.dev>"
    assert body["from"] != lead_object().email and body["to"] == ["owner@example.com"]
    assert body["reply_to"] == "prospect@example.com"
    assert body["subject"] == "New Freelance Project Lead - Test Person"
    for value in ("Name: Test Person", "Email: prospect@example.com", "Phone: +30 2100000000",
                  "Company: Example Practice", "Healthcare", "New website", "Booking system",
                  "€1,000–€2,000", "Within 1 month", "Greek Ελληνικά and English project."):
        assert value in body["text"]
    assert "<strong>Name</strong><br>Test Person" in body["html"]
    assert "PRIVATE" not in body["text"] and "internal_notes" not in body


@pytest.mark.parametrize("body_kind", ["plain", "html", "multipart"])
def test_resend_extracts_available_body_variants(app, monkeypatch, body_kind):
    resend_config(app)
    message = EmailMessage()
    message["Subject"] = "Synthetic body test"
    if body_kind == "plain":
        message.set_content("plain-only content")
    elif body_kind == "html":
        message.set_content("<p>html-only content</p>", subtype="html")
    else:
        message.set_content("plain multipart content")
        message.add_alternative("<p>html multipart content</p>", subtype="html")
    captured = {}
    def accepted(payload, options=None):
        captured["body"] = payload
        return {"id": "email_synthetic"}
    monkeypatch.setattr(resend.Emails, "send", accepted)
    with app.app_context():
        assert mail.send_message(message) == "sent"
    payload = captured["body"]
    if body_kind == "plain":
        assert payload["text"].strip() == "plain-only content"
        assert "html" not in payload
    elif body_kind == "html":
        assert payload["html"].strip() == "<p>html-only content</p>"
        assert "text" not in payload
    else:
        assert payload["text"].strip() == "plain multipart content"
        assert payload["html"].strip() == "<p>html multipart content</p>"


def test_resend_rejects_message_without_usable_body(app, monkeypatch, caplog):
    resend_config(app)
    message = EmailMessage()
    message["Subject"] = "Empty body test"
    message.set_content("  \n  ")
    send = MagicMock()
    monkeypatch.setattr(resend.Emails, "send", send)
    with app.app_context(), pytest.raises(mail.MailDeliveryError) as exc:
        mail.send_message(message)
    assert exc.value.category == "validation" and not send.called
    assert API_KEY not in caplog.text


@pytest.mark.parametrize("error,category", [
    (resend.exceptions.InvalidApiKeyError("private API key", "invalid_api_key", 403), "authentication"),
    (resend.exceptions.ValidationError(PRIVATE_BODY, "validation_error", 422), "validation"),
    (resend.exceptions.RateLimitError(PRIVATE_BODY, "rate_limit_exceeded", 429), "rate_limit"),
    (resend.exceptions.ResendError(500, "application_error", PRIVATE_BODY, "private action"), "provider_error"),
    (resend.exceptions.ResendError(403, "application_error", "Cloudflare 1010 " + API_KEY, ""), "provider_error"),
    (resend.exceptions.ResendError(401, "application_error", PRIVATE_BODY, ""), "provider_error"),
    (resend.exceptions.ResendError(500, "HttpClientError", PRIVATE_BODY + API_KEY, ""), "network"),
])
def test_resend_sdk_error_is_categorized_and_redacted(app, monkeypatch, caplog, error, category):
    resend_config(app)
    monkeypatch.setattr(resend.Emails, "send", MagicMock(side_effect=error))
    with app.app_context(), pytest.raises(mail.MailDeliveryError) as exc:
        mail.notify_lead(lead_object(description=PRIVATE_BODY))
    assert exc.value.category == category
    assert category in caplog.text and "provider=resend" in caplog.text
    assert API_KEY not in caplog.text and PRIVATE_BODY not in caplog.text and "private API key" not in caplog.text


@pytest.mark.parametrize("response", [None, {}, {"id": ""}, {"id": None}])
def test_missing_sdk_message_id_is_not_marked_sent(app, monkeypatch, response):
    resend_config(app)
    monkeypatch.setattr(resend.Emails, "send", MagicMock(return_value=response))
    with app.app_context(), pytest.raises(mail.MailDeliveryError) as exc:
        mail.notify_lead(lead_object())
    assert exc.value.category == "provider_error"


def test_untrusted_lead_html_is_escaped(app, monkeypatch):
    resend_config(app)
    captured = {}
    def accepted(payload, options=None):
        captured["body"] = payload
        return {"id": "email_synthetic"}
    monkeypatch.setattr(resend.Emails, "send", accepted)
    with app.app_context():
        mail.notify_lead(lead_object(description="<script>alert(1)</script> & details"))
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; details" in captured["body"]["html"]
    assert "<script>" not in captured["body"]["html"]


@pytest.mark.parametrize("name,email", [("Client\r\nBcc: attacker@example.com", "valid@example.com"),
    ("Client", "bad\r\nBcc:attacker@example.com")])
def test_unsafe_reply_or_subject_header_rejected_before_network(app, monkeypatch, name, email):
    resend_config(app)
    send = MagicMock()
    monkeypatch.setattr(resend.Emails, "send", send)
    with app.app_context(), pytest.raises(mail.MailDeliveryError) as exc:
        mail.notify_lead(lead_object(name=name, email=email))
    assert exc.value.category == "validation" and not send.called


def test_explicit_resend_never_falls_back_to_smtp(app, monkeypatch):
    resend_config(app)
    accepted = MagicMock(return_value={"id": "email_synthetic"})
    smtp = MagicMock(side_effect=AssertionError("SMTP fallback forbidden"))
    monkeypatch.setattr(resend.Emails, "send", accepted)
    monkeypatch.setattr(smtplib, "SMTP", smtp)
    with app.app_context():
        assert mail.notify_lead(lead_object()) == "sent"
    smtp.assert_not_called()


def test_resend_configuration_does_not_require_smtp_and_disabled_needs_no_credentials(app, monkeypatch):
    app.config.update(MAIL_ENABLED=True, MAIL_PROVIDER="resend", RESEND_API_KEY=API_KEY,
                      RESEND_FROM_ADDRESS="Website Leads <onboarding@resend.dev>", MAIL_ADDRESS="owner@example.com",
                      MAIL_APP_PASSWORD="", MAIL_HOST="")
    monkeypatch.setattr(resend.Emails, "send", lambda *args, **kwargs: {"id": "email_synthetic"})
    with app.app_context():
        assert mail.notify_lead(lead_object()) == "sent"
    app.config.update(MAIL_ENABLED=False, RESEND_API_KEY="", RESEND_FROM_ADDRESS="", MAIL_ADDRESS="")
    with app.app_context():
        assert mail.notify_lead(lead_object()) == "disabled"


def test_resend_config_validation_and_no_implicit_provider_selection(monkeypatch):
    common = {"TESTING": True, "SECRET_KEY": "test-only-key", "MAIL_ENABLED": True,
              "MAIL_ADDRESS": "owner@example.com", "RESEND_API_KEY": API_KEY,
              "RESEND_FROM_ADDRESS": "Website Leads <onboarding@resend.dev>"}
    app = create_app({**common, "MAIL_PROVIDER": "resend"})
    assert app.config["MAIL_PROVIDER"] == "resend"
    with pytest.raises(ValueError, match="MAIL_PROVIDER"):
        create_app({**common, "MAIL_PROVIDER": "smtp-ish"})
    with pytest.raises(ValueError, match="RESEND_API_KEY"):
        create_app({**common, "MAIL_PROVIDER": "resend", "RESEND_API_KEY": ""})
    with pytest.raises(ValueError, match="RESEND_FROM_ADDRESS"):
        create_app({**common, "MAIL_PROVIDER": "resend", "RESEND_FROM_ADDRESS": "invalid sender"})
    disabled = create_app({"TESTING": True, "SECRET_KEY": "test-only-key", "MAIL_ENABLED": False,
                           "MAIL_PROVIDER": "resend", "RESEND_API_KEY": "", "RESEND_FROM_ADDRESS": "", "MAIL_ADDRESS": ""})
    assert disabled.config["MAIL_PROVIDER"] == "resend"


def test_public_failed_resend_keeps_committed_lead(app, client, lead_data, monkeypatch, caplog):
    resend_config(app, MAIL_ADDRESS="xentesvasilis@gmail.com")
    monkeypatch.setattr(resend.Emails, "send", MagicMock(side_effect=resend.exceptions.InvalidApiKeyError(API_KEY, "invalid_api_key", 403)))
    lead_data["description"] = PRIVATE_BODY
    response = client.post("/contact?lang=en", data=lead_data)
    assert response.status_code == 303
    with app.app_context():
        lead = db.session.scalar(db.select(Lead))
        assert lead is not None and lead.description == PRIVATE_BODY and lead.email_status == "failed"
    assert API_KEY not in caplog.text and PRIVATE_BODY not in caplog.text


def test_cli_smoke_test_uses_mocked_resend(app, monkeypatch):
    resend_config(app, MAIL_ADDRESS="owner@example.com")
    send = MagicMock(return_value={"id": "email_synthetic"})
    monkeypatch.setattr(resend.Emails, "send", send)
    result = app.test_cli_runner().invoke(args=["mail-smoke-test"])
    assert result.exit_code == 0, result.output
    assert "provider=resend" in result.output and API_KEY not in result.output
    payload = send.call_args.args[0]
    assert payload["subject"] == "Freelance website delivery test"
    assert "No customer information" in payload["text"]
    assert "html" not in payload


def test_cli_smoke_test_failure_is_generic_and_redacted(app, monkeypatch):
    resend_config(app, MAIL_ADDRESS="owner@example.com")
    error = resend.exceptions.ResendError(403, "application_error", PRIVATE_BODY + API_KEY, "private details")
    monkeypatch.setattr(resend.Emails, "send", MagicMock(side_effect=error))
    result = app.test_cli_runner().invoke(args=["mail-smoke-test"])
    assert result.exit_code != 0
    assert "Email test failed via provider=resend" in result.output
    assert API_KEY not in result.output and PRIVATE_BODY not in result.output
