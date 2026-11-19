"""CLI behavior on explicitly synthetic software fixtures; no Olist results."""

import json

from shipsignal.cli import main


def test_cli_inspection_and_source_validation(fixture_source, tmp_path, monkeypatch):
    output = tmp_path / "inspection.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "shipsignal",
            "inspect",
            "--source",
            str(fixture_source),
            "--archive",
            str(tmp_path / "archive"),
            "--output",
            str(output),
            "--source-url",
            "synthetic-software-test-fixtures",
        ],
    )
    assert main() == 0
    assert output.with_suffix(".dictionary.md").exists()
    report = tmp_path / "validation.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "shipsignal",
            "validate",
            "--source-only",
            "--manifest",
            str(output),
            "--output",
            str(report),
        ],
    )
    assert main() == 0
    assert json.loads(report.read_text())["database_checked"] is False


def test_partial_release_is_not_certified(fixture_source, tmp_path, monkeypatch):
    (fixture_source / "olist_order_payments_dataset.csv").unlink()
    output = tmp_path / "inspection.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "shipsignal",
            "inspect",
            "--source",
            str(fixture_source),
            "--archive",
            str(tmp_path / "archive"),
            "--output",
            str(output),
            "--source-url",
            "synthetic-software-test-fixtures",
        ],
    )
    assert main() == 0
    monkeypatch.setattr(
        "sys.argv",
        [
            "shipsignal",
            "validate",
            "--source-only",
            "--manifest",
            str(output),
            "--output",
            str(tmp_path / "validation.json"),
        ],
    )
    assert main() == 1
