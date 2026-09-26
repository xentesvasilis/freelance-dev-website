import pytest

from app.extensions import db
from app.models import Admin


@pytest.mark.parametrize("password", ["short", "dev-only-change-before-launch", "Password123456789!",
                                     "ChangeMe123456789!", "admin123456789012345", "a" * 20,
                                     "default-password-1234", "1234567890123456", "test-password-only-for-development", "x" * 257])
def test_admin_rejects_default_passwords(app, password):
    result = app.test_cli_runner().invoke(args=["create-admin"],
                                        input=f"owner@example.com\n{password}\n{password}\n")
    assert result.exit_code != 0
    assert password not in result.output
    with app.app_context():
        assert db.session.scalar(db.select(Admin).where(Admin.username == "owner@example.com")) is None


def test_admin_confirmation_and_invalid_email(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["create-admin"], input="invalid\n").exit_code != 0
    result = runner.invoke(args=["create-admin"], input="owner@example.com\none-private-passphrase\nanother-private-passphrase\n")
    assert result.exit_code != 0
    assert "one-private-passphrase" not in result.output
    assert "another-private-passphrase" not in result.output
    with app.app_context():
        assert db.session.scalar(db.select(Admin).where(Admin.username == "owner@example.com")) is None


def test_admin_password_options_not_accepted(app):
    assert app.test_cli_runner().invoke(args=["create-admin", "--password", "unused"]).exit_code != 0


def test_admin_prompt_hides_password(app, monkeypatch):
    import app.cli as cli
    calls = []
    def prompt(label, **kwargs):
        calls.append((label, kwargs))
        return "owner@example.com" if label == "Admin email" else "unique-long-testing-passphrase"
    monkeypatch.setattr(cli.click, "prompt", prompt)
    assert app.test_cli_runner().invoke(args=["create-admin"]).exit_code == 0
    assert calls[1] == ("Password", {"hide_input": True, "confirmation_prompt": True})
