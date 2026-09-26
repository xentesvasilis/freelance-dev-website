import importlib.util
from pathlib import Path


def load_tool():
    spec = importlib.util.spec_from_file_location("staging_verify", Path("scripts/staging_verify.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_is_separate_idempotent_and_secret_safe(tmp_path, monkeypatch, capsys):
    tool = load_tool()
    monkeypatch.setattr(tool, "STAGING_ENV", tmp_path / ".env.local-staging")
    real = tmp_path / ".env"
    real.write_text("do not read or change", encoding="utf-8")
    tool.prepare()
    first = tool.STAGING_ENV.read_text(encoding="utf-8")
    value = first.split("LOCAL_STAGING_DB_PASSWORD=", 1)[1].strip()
    assert len(value) == 64
    tool.prepare()
    assert tool.STAGING_ENV.read_text(encoding="utf-8") == first
    assert real.read_text(encoding="utf-8") == "do not read or change"
    assert value not in capsys.readouterr().out


def test_missing_docker_is_blocked_not_passed(monkeypatch, capsys):
    tool = load_tool()
    monkeypatch.setattr(tool.shutil, "which", lambda name: None)
    assert tool.verify() == 2
    assert "BLOCKED" in capsys.readouterr().out
