from email.message import EmailMessage
import re

import click
from email_validator import EmailNotValidError, validate_email

from .extensions import db
from .mail import send_message
from .models import Admin


def register_cli(app):
    @app.cli.command("seed-dev")
    def seed_dev():
        """Create a DEVELOPMENT-ONLY admin, without overwriting existing credentials."""
        if app.config["PRODUCTION"]:
            raise click.ClickException("seed-dev is disabled in production")
        if db.session.scalar(db.select(Admin).where(Admin.username == "dev-admin")):
            click.echo("Development admin already exists; no changes.")
            return
        admin = Admin(username="dev-admin")
        admin.set_password("dev-only-change-before-launch")
        db.session.add(admin)
        db.session.commit()
        click.echo("Development admin created. See README for development-only credentials.")

    @app.cli.command("create-admin")
    def create_admin():
        """Create an admin interactively; use the email as the login username."""
        email = click.prompt("Admin email", type=str).strip()
        try:
            username = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            raise click.ClickException("Enter a valid admin email address") from None
        if len(username) > 120:
            raise click.ClickException("Admin email must be at most 120 characters")
        if db.session.scalar(db.select(Admin).where(Admin.username == username)):
            raise click.ClickException("Admin already exists")
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        normalized = re.sub(r"[^a-z0-9]", "", password.lower())
        if not 16 <= len(password) <= 256:
            raise click.ClickException("Use a password of 16–256 characters")
        if (len(set(password)) < 5 or normalized.isdigit() or normalized.startswith(("password", "changeme", "admin", "default", "development", "devonly", "qwerty", "letmein", "welcome", "testpassword", "abcdef", "0123456789"))
                or normalized == username.split("@")[0]):
            raise click.ClickException("Choose a unique password, not a default or development password")
        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo("Admin created.")

    @app.cli.command("mail-smoke-test")
    def mail_smoke_test():
        """Explicitly send a harmless test using MAIL_PROVIDER."""
        if not app.config["MAIL_ENABLED"]:
            raise click.ClickException("Email is disabled; configure MAIL_ENABLED and the selected provider first")
        message = EmailMessage()
        message["Subject"] = "Freelance website delivery test"
        message.set_content("This is a configuration test. No customer information is included.")
        try:
            send_message(message)
        except Exception:
            raise click.ClickException(f"Email test failed via provider={app.config['MAIL_PROVIDER']}. Check its configuration privately.") from None
        click.echo(f"Email test accepted via provider={app.config['MAIL_PROVIDER']}.")
