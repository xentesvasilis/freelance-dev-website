import io
import json
import smtplib
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from unittest.mock import MagicMock

import pytest

from app import create_app
from app import mail
from app.extensions import db
from app.models import Lead


API_KEY = "synthetic-resend-key-never-real"
PRIVATE_BODY = "PRIVATE_LEAD_BODY_MARKER"


class FakeResponse:
    status = 200

    def __init__(self, body=b'{"id":"email_synthetic"}'):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return self.body[:limit]


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
    def accepted(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()
    monkeypatch.setattr(mail, "urlopen", accepted)
    with app.app_context():
        result = mail.notify_lead(lead_object(), idempotency_key="signed-test-retry-key")
    req = captured["request"]
    body = json.loads(req.data)
    assert req.full_url == "https://api.resend.com/emails" and req.get_method() == "POST"
    assert req.get_header("Authorization") == "Bearer " + API_KEY
    assert req.get_header("Idempotency-key") == "signed-test-retry-key"
    assert captured["timeout"] == 10 and result == "sent"
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


@pytest.mark.parametrize("status,category", [(401, "authentication"), (403, "authentication"),
    (400, "validation"), (422, "validation"), (429, "rate_limit"), (500, "provider_error")])
def test_resend_http_failure_is_categorized_and_redacted(app, monkeypatch, caplog, status, category):
    resend_config(app)
    def reject(*args, **kwargs):
        raise HTTPError(mail.RESEND_ENDPOINT, status, "private API key " + API_KEY, {}, io.BytesIO(PRIVATE_BODY.encode()))
    monkeypatch.setattr(mail, "urlopen", reject)
    with app.app_context(), pytest.raises(mail.MailDeliveryError) as exc:
        mail.notify_lead(lead_object(description=PRIVATE_BODY))
    assert exc.value.category == category
    assert category in caplog.text and "provider=resend" in caplog.text
    assert API_KEY not in caplog.text and PRIVATE_BODY not in caplog.text and "private API key" not in caplog.text


def test_resend_network_failure_is_redacted(app, monkeypatch, caplog):
    resend_config(app)
    monkeypatch.setattr(mail, "urlopen", MagicMock(side_effect=URLError("private " + API_KEY + PRIVATE_BODY)))
    with app.app_context(), pytest.raises(mail.MailDeliveryError) as exc:
        mail.notify_lead(lead_object(description=PRIVATE_BODY))
    assert exc.value.category == "network"
    assert API_KEY not in caplog.text and PRIVATE_BODY not in caplog.text


def test_malformed_success_response_is_not_marked_sent(app, monkeypatch):
    resend_config(app)
    monkeypatch.setattr(mail, "urlopen", lambda *args, **kwargs: FakeResponse(b'{"unexpected":"shape"}'))
    with app.app_context(), pytest.raises(mail.MailDeliveryError) as exc:
        mail.notify_lead(lead_object())
    assert exc.value.category == "provider_error"


def test_untrusted_lead_html_is_escaped(app, monkeypatch):
    resend_config(app)
    captured = {}
    def accepted(request, timeout):
        captured["body"] = json.loads(request.data)
        return FakeResponse()
    monkeypatch.setattr(mail, "urlopen", accepted)
    with app.app_context():
        mail.notify_lead(lead_object(description="<script>alert(1)</script> & details"))
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; details" in captured["body"]["html"]
    assert "<script>" not in captured["body"]["html"]


@pytest.mark.parametrize("name,email", [("Client\r\nBcc: attacker@example.com", "valid@example.com"),
    ("Client", "bad\r\nBcc:attacker@example.com")])
def test_unsafe_reply_or_subject_header_rejected_before_network(app, monkeypatch, name, email):
    resend_config(app)
    send = MagicMock()
    monkeypatch.setattr(mail, "urlopen", send)
    with app.app_context(), pytest.raises(mail.MailDeliveryError) as exc:
        mail.notify_lead(lead_object(name=name, email=email))
    assert exc.value.category == "validation" and not send.called


def test_explicit_resend_never_falls_back_to_smtp(app, monkeypatch):
    resend_config(app)
    accepted = MagicMock(return_value=FakeResponse())
    smtp = MagicMock(side_effect=AssertionError("SMTP fallback forbidden"))
    monkeypatch.setattr(mail, "urlopen", accepted)
    monkeypatch.setattr(smtplib, "SMTP", smtp)
    with app.app_context():
        assert mail.notify_lead(lead_object()) == "sent"
    smtp.assert_not_called()


def test_resend_configuration_does_not_require_smtp_and_disabled_needs_no_credentials(app, monkeypatch):
    app.config.update(MAIL_ENABLED=True, MAIL_PROVIDER="resend", RESEND_API_KEY=API_KEY,
                      RESEND_FROM_ADDRESS="Website Leads <onboarding@resend.dev>", MAIL_ADDRESS="owner@example.com",
                      MAIL_APP_PASSWORD="", MAIL_HOST="")
    monkeypatch.setattr(mail, "urlopen", lambda *args, **kwargs: FakeResponse())
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
    monkeypatch.setattr(mail, "urlopen", MagicMock(side_effect=HTTPError(mail.RESEND_ENDPOINT, 401, API_KEY, {}, io.BytesIO(b"secret response"))))
    lead_data["description"] = PRIVATE_BODY
    response = client.post("/contact?lang=en", data=lead_data)
    assert response.status_code == 303
    with app.app_context():
        lead = db.session.scalar(db.select(Lead))
        assert lead is not None and lead.description == PRIVATE_BODY and lead.email_status == "failed"
    assert API_KEY not in caplog.text and PRIVATE_BODY not in caplog.text and "secret response" not in caplog.text


def test_cli_smoke_test_uses_mocked_resend(app, monkeypatch):
    resend_config(app, MAIL_ADDRESS="owner@example.com")
    import app.cli as cli
    send = MagicMock()
    monkeypatch.setattr(cli, "send_message", send)
    result = app.test_cli_runner().invoke(args=["mail-smoke-test"])
    assert result.exit_code == 0, result.output
    assert "provider=resend" in result.output and API_KEY not in result.output
    message = send.call_args.args[0]
    assert message["Subject"] == "Freelance website delivery test"
    assert "No customer information" in message.get_content()
