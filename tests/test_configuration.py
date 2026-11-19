"""Regression checks for committed configuration: no populated password defaults."""

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_templates_have_no_password_or_connection_secret():
    text = (ROOT / ".env.example").read_text()
    values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    assert values["POSTGRES_PASSWORD"] == ""
    assert values["DATABASE_URL"] == ""
    compose = (ROOT / "compose.yaml").read_text()
    assert "${POSTGRES_PASSWORD:?" in compose
    assert "${POSTGRES_PASSWORD:-" not in compose


def test_environment_files_are_ignored_except_empty_template():
    rules = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in rules
    assert ".env.*" in rules
    assert "!.env.example" in rules


def test_local_setup_generates_distinct_private_values_without_overwriting(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location(
        "init_local_env", ROOT / "scripts/init_local_env.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first, second = tmp_path / "first.env", tmp_path / "second.env"
    module.create_env(first)
    module.create_env(second)
    assert first.read_text() != second.read_text()
    original = first.read_text()
    with pytest.raises(FileExistsError):
        module.create_env(first)
    assert first.read_text() == original
    assert capsys.readouterr().out == ""
    if os.name == "posix":
        assert first.stat().st_mode & 0o777 == 0o600
