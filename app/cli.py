from email.message import EmailMessage

import click

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
    @click.option("--username", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(username, password):
        """Create an admin using a hidden password prompt."""
        if app.config["PRODUCTION"] and username == "dev-admin":
            raise click.ClickException("The development username is prohibited in production")
        if not 1 <= len(username) <= 120 or len(password) < 16 or len(password) > 256:
            raise click.ClickException("Use a username up to 120 characters and a password of 16–256 characters")
        if db.session.scalar(db.select(Admin).where(Admin.username == username)):
            raise click.ClickException("Username already exists")
        if password == "dev-only-change-before-launch":
            raise click.ClickException("Do not use the documented development password")
        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo("Admin created.")

    @app.cli.command("mail-smoke-test")
    def mail_smoke_test():
        """Explicitly send a harmless SMTP test from/to MAIL_ADDRESS."""
        if not app.config["MAIL_ENABLED"]:
            raise click.ClickException("Set MAIL_ENABLED=true and configure SMTP first")
        message = EmailMessage()
        message["Subject"] = "Freelance website SMTP test"
        message.set_content("This is a configuration test. No customer information is included.")
        try:
            send_message(message)
        except Exception:
            raise click.ClickException("SMTP test failed. Check host, TLS, port and credentials privately.") from None
        click.echo("SMTP test sent successfully.")
