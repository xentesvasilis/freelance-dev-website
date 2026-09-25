import smtplib
from pathlib import Path
from unittest.mock import MagicMock

from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from app.models import Admin


def test_seed_dev_idempotent(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-dev"]).exit_code == 0
    with app.app_context():
        admin = db.session.scalar(db.select(Admin).where(Admin.username == "dev-admin"))
        original_hash = admin.password_hash
        assert admin.check_password("dev-only-change-before-launch")
    assert runner.invoke(args=["seed-dev"]).exit_code == 0
    with app.app_context():
        assert db.session.scalar(db.select(Admin).where(Admin.username == "dev-admin")).password_hash == original_hash
    app.config["PRODUCTION"] = True
    assert runner.invoke(args=["seed-dev"]).exit_code != 0


def test_smoke_test_disabled_and_mocked(app, monkeypatch):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["mail-smoke-test"]).exit_code != 0
    app.config.update(MAIL_ENABLED=True, MAIL_APP_PASSWORD="mock-only", MAIL_USE_TLS=True, MAIL_PORT=587)
    connection = MagicMock()
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(return_value=connection))
    result = runner.invoke(args=["mail-smoke-test"])
    assert result.exit_code == 0
    assert "mock-only" not in result.output
    message = connection.__enter__.return_value.send_message.call_args.args[0]
    assert message["To"] == message["From"] == "xentesvasilis@gmail.com"
    assert "No customer information" in message.get_content()
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(side_effect=RuntimeError("mock-only")))
    result = runner.invoke(args=["mail-smoke-test"])
    assert result.exit_code != 0
    assert "mock-only" not in result.output


def test_create_admin(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-admin", "--username", "owner", "--password", "long-test-password-only"])
    assert result.exit_code == 0
    with app.app_context():
        user = db.session.scalar(db.select(Admin).where(Admin.username == "owner"))
        assert user.check_password("long-test-password-only")
    assert runner.invoke(args=["create-admin", "--username", "owner", "--password", "long-test-password-only"]).exit_code != 0


def test_migrations_empty_sqlite_upgrade_downgrade(tmp_path):
    app = create_app({"TESTING": True, "PRODUCTION": False, "SECRET_KEY": "migration-tests-only", "CALENDLY_SCHEDULING_URL": "",
                      "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (tmp_path / "migration.db").as_posix(), "RATELIMIT_ENABLED": False})
    runner = app.test_cli_runner()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        inspector = inspect(db.engine)
        assert {"admin", "lead", "portfolio_project", "alembic_version"}.issubset(inspector.get_table_names())
        assert {"public_id", "email_status", "privacy_accepted_at", "requirements_json"}.issubset({c["name"] for c in inspector.get_columns("lead")})
    result = runner.invoke(args=["db", "check"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(args=["db", "downgrade", "base"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert "lead" not in inspect(db.engine).get_table_names()
    assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
