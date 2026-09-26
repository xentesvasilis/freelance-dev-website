"""Transactional notifications using explicitly selected Resend HTTPS or SMTP."""
import json
import smtplib
import socket
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from email_validator import EmailNotValidError, validate_email
from flask import current_app

from .content import CHOICES

RESEND_ENDPOINT = "https://api.resend.com/emails"


class MailDeliveryError(Exception):
    """Safe provider category only; never carries provider payload or credentials."""
    def __init__(self, category):
        self.category = category if category in {"authentication", "validation", "rate_limit", "network", "provider_error", "unknown"} else "unknown"
        super().__init__(self.category)


def _safe_address(value):
    if not value or any(char in value for char in "\r\n"):
        raise MailDeliveryError("validation")
    try:
        return validate_email(value, check_deliverability=False).normalized
    except EmailNotValidError:
        raise MailDeliveryError("validation") from None


def _safe_sender(value):
    if not value or any(char in value for char in "\r\n"):
        raise MailDeliveryError("validation")
    display, address = parseaddr(value)
    _safe_address(address)
    if (not address or (display and formataddr((display, address)) != value)
            or (not display and address != value) or "," in value or ";" in value):
        raise MailDeliveryError("validation")
    return value


def _resend_category(status):
    if status in (401, 403):
        return "authentication"
    if status in (400, 422):
        return "validation"
    if status == 429:
        return "rate_limit"
    return "provider_error"


def _body_content(message, subtype):
    content_type = f"text/{subtype}"
    if message.get_content_type() == content_type:
        part = message
    else:
        part = message.get_body(preferencelist=(subtype,))
    if part is None or part.get_content_type() != content_type:
        return None
    try:
        content = part.get_content()
    except (LookupError, TypeError, ValueError):
        return None
    if not isinstance(content, str) or not content.strip():
        return None
    return content


def _send_resend(message, idempotency_key=None):
    config = current_app.config
    sender = _safe_sender(config["RESEND_FROM_ADDRESS"])
    recipient = _safe_address(config["MAIL_ADDRESS"])
    payload = {
        "from": sender,
        "to": [recipient],
        "subject": str(message["Subject"]),
    }
    text_body = _body_content(message, "plain")
    html_body = _body_content(message, "html")
    if text_body is not None:
        payload["text"] = text_body
    if html_body is not None:
        payload["html"] = html_body
    if text_body is None and html_body is None:
        raise MailDeliveryError("validation")
    reply_to = message.get("Reply-To")
    if reply_to:
        payload["reply_to"] = _safe_address(str(reply_to))
    headers = {"Authorization": "Bearer " + config["RESEND_API_KEY"], "Content-Type": "application/json"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(RESEND_ENDPOINT, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise MailDeliveryError(_resend_category(response.status))
            result = json.loads(response.read(65536).decode("utf-8"))
    except HTTPError as exc:
        raise MailDeliveryError(_resend_category(exc.code)) from None
    except (URLError, TimeoutError, socket.timeout, ssl.SSLError, OSError):
        raise MailDeliveryError("network") from None
    except MailDeliveryError:
        raise
    except Exception:
        raise MailDeliveryError("provider_error") from None
    if not isinstance(result, dict) or not isinstance(result.get("id"), str) or not result["id"]:
        raise MailDeliveryError("provider_error")
    return "sent"


def _send_smtp(message):
    config = current_app.config
    address = _safe_address(config["MAIL_ADDRESS"])
    if not config["MAIL_APP_PASSWORD"] or not config["MAIL_HOST"]:
        raise MailDeliveryError("authentication")
    if not config["MAIL_USE_TLS"] and config["MAIL_PORT"] != 465:
        raise MailDeliveryError("validation")
    message["From"] = address
    message["To"] = address
    try:
        if config["MAIL_PORT"] == 465:
            connection = smtplib.SMTP_SSL(config["MAIL_HOST"], 465, timeout=10, context=ssl.create_default_context())
        else:
            connection = smtplib.SMTP(config["MAIL_HOST"], config["MAIL_PORT"], timeout=10)
        with connection as smtp:
            if config["MAIL_USE_TLS"] and config["MAIL_PORT"] != 465:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(address, config["MAIL_APP_PASSWORD"])
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError:
        raise MailDeliveryError("authentication") from None
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
        raise MailDeliveryError("validation") from None
    except (smtplib.SMTPException, OSError, TimeoutError, socket.timeout):
        raise MailDeliveryError("network") from None
    except Exception:
        raise MailDeliveryError("unknown") from None
    return "sent"


def send_message(message, idempotency_key=None):
    config = current_app.config
    if not config["MAIL_ENABLED"]:
        return "disabled"
    provider = config["MAIL_PROVIDER"]
    try:
        if provider == "resend":
            return _send_resend(message, idempotency_key=idempotency_key)
        if provider == "smtp":
            return _send_smtp(message)
        raise MailDeliveryError("validation")
    except MailDeliveryError as exc:
        current_app.logger.warning("Lead notification failed via provider=%s reason=%s", provider, exc.category)
        raise


def choice_label(group, value):
    return next((label["en"] for key, label in CHOICES[group] if key == value), value)


def notification_message(lead):
    name = str(lead.name)
    email = _safe_address(str(lead.email))
    if any(char in name for char in "\r\n"):
        raise MailDeliveryError("validation")
    message = EmailMessage()
    message["Subject"] = f"New Freelance Project Lead - {name}"
    message["Reply-To"] = email
    fields = [
        ("Name", name), ("Email", email), ("Phone", lead.phone or "—"),
        ("Company", lead.company or "—"), ("Industry", choice_label("industry", lead.industry)),
        ("Requirements", ", ".join(choice_label("requirements", x) for x in lead.requirements_json)),
        ("Budget", choice_label("budget", lead.budget_range)),
        ("Timeframe", choice_label("timeframe", lead.timeframe)),
        ("Description", lead.description),
    ]
    message.set_content("\n\n".join(f"{key}: {value}" for key, value in fields))
    message.add_alternative("<h1>New project enquiry</h1>" + "".join(
        f"<p><strong>{escape(key)}</strong><br>{escape(value).replace(chr(10), '<br>')}</p>" for key, value in fields
    ), subtype="html")
    return message


def notify_lead(lead, idempotency_key=None):
    if not current_app.config["MAIL_ENABLED"]:
        return "disabled"
    try:
        return send_message(notification_message(lead), idempotency_key=idempotency_key)
    except MailDeliveryError:
        raise
    except Exception:
        provider = current_app.config["MAIL_PROVIDER"]
        current_app.logger.warning("Lead notification failed via provider=%s reason=unknown", provider)
        raise MailDeliveryError("unknown") from None
