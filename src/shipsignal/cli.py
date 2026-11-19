"""Explicit batch CLI; never silently downloads data or starts later milestones."""

import argparse
import csv
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from .database import ingest, validate_database, verify_sources
from .profile import inspect
from .validation import quality_checks


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dictionary(manifest):
    lines = [
        "# Observed source dictionary",
        "",
        "Generated from actual CSV headers. All raw database fields are text.",
        "Missing means empty or whitespace-only; values are preserved unchanged.",
        "",
    ]
    for table, info in manifest["tables"].items():
        lines += [
            f"## {table}",
            "",
            f"Source: `{info['file']}`; records: {info['rows']}",
            "",
            "| Column | Empty | Whitespace-only | Distinct including empty |",
            "|---|---:|---:|---:|",
        ]
        for col, fields in info["fields"].items():
            lines.append(
                f"| {col} | {fields['empty']} | {fields['whitespace_only']} | "
                f"{fields['distinct_including_empty']} |"
            )
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("inspect", help="archive, discover and profile actual CSVs")
    scan.add_argument("--source", type=Path, default=Path("data/raw"))
    scan.add_argument("--archive", type=Path, default=Path("data/manifests"))
    scan.add_argument("--output", type=Path, default=Path("reports/inspection.json"))
    scan.add_argument("--source-url", required=True, help="release URL or test-fixture provenance")
    for command in ("ingest", "validate"):
        option = sub.add_parser(command)
        option.add_argument("--manifest", type=Path, default=Path("reports/inspection.json"))
        if command == "validate":
            option.add_argument("--output", type=Path, default=Path("reports/validation.json"))
            option.add_argument("--source-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            manifest = inspect(args.source, args.archive, args.source_url)
            manifest["inspected_at"] = datetime.now(UTC).isoformat()
            write_json(args.output, manifest)
            args.output.with_suffix(".dictionary.md").write_text(
                dictionary(manifest), encoding="utf-8"
            )
            print(f"Inspected {len(manifest['tables'])} tables. Evidence: {args.output}")
            return 0
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.command == "ingest":
            result = ingest(os.environ["DATABASE_URL"], manifest)
            print(json.dumps(result))
            return 0
        verify_sources(manifest)
        checks = quality_checks(manifest)
        database_checked = not args.source_only
        if database_checked:
            checks += validate_database(os.environ["DATABASE_URL"], manifest)
        result = {
            "snapshot_id": manifest["snapshot_id"],
            "database_checked": database_checked,
            "checked_at": datetime.now(UTC).isoformat(),
            "passed": all(c["passed"] for c in checks),
            "checks": checks,
        }
        write_json(args.output, result)
        print(f"{sum(c['passed'] for c in checks)}/{len(checks)} checks passed; {args.output}")
        return 0 if result["passed"] else 1
    except (ValueError, KeyError, OSError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except psycopg.Error as exc:
        # psycopg errors can contain connection parameters; don't print credentials.
        print(
            f"ERROR: {type(exc).__name__}; check database availability and source contract.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
