"""SMTP transport; never logs credentials or customer content."""
import smtplib
import ssl
from email.message import EmailMessage
from html import escape

from flask import current_app

from .content import CHOICES


def send_message(message):
    config = current_app.config
    if not config["MAIL_ENABLED"]:
        return "disabled"
    if not config["MAIL_APP_PASSWORD"]:
        raise RuntimeError("SMTP credential is missing")
    # Refuse cleartext authentication even when a production environment is misconfigured.
    if not config["MAIL_USE_TLS"] and config["MAIL_PORT"] != 465:
        raise RuntimeError("SMTP requires STARTTLS or implicit TLS on port 465")
    address = config["MAIL_ADDRESS"]
    message["From"] = address
    message["To"] = address
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
    return "sent"


def choice_label(group, value):
    return next((label["en"] for key, label in CHOICES[group] if key == value), value)


def notify_lead(lead):
    message = EmailMessage()
    # Defense in depth: headers never accept untrusted CR/LF.
    name = " ".join(lead.name.splitlines())
    message["Subject"] = f"New Freelance Project Lead - {name}"
    fields = [
        ("Name", lead.name), ("Email", lead.email), ("Phone", lead.phone or "—"),
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
    return send_message(message)
