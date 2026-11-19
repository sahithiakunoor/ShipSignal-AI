"""Streaming profiles; bounded to one table, with exact distinct/key sets in memory."""

import hashlib
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .contracts import CANDIDATES, DATES, FILES, KEYS, MONEY, RELATIONSHIPS
from .source import canonical_update, headers, preserve, rows


def missing(value):
    return not value.strip()


def amount(value):
    number = Decimal(value)
    if not number.is_finite():
        raise InvalidOperation("nonfinite money")
    return number


def timestamp(value):
    # Naive ISO source timestamps: no timezone conversion or UTC assumption.
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def profile_file(path: Path, table: str) -> dict:
    columns = headers(path)
    fields = {c: {"empty": 0, "whitespace_only": 0, "distinct": set()} for c in columns}
    key_specs = ([KEYS[table]] if table in KEYS else []) + CANDIDATES.get(table, [])
    key_counts = {tuple(k): Counter() for k in key_specs if set(k) <= set(columns)}
    key_missing = Counter()
    dates = {
        c: {"missing": 0, "invalid": 0, "min": None, "max": None}
        for c in DATES.get(table, [])
        if c in columns
    }
    money = {
        c: {"sum": Decimal(0), "invalid": 0, "missing": 0, "negative": 0}
        for c in MONEY.get(table, [])
        if c in columns
    }
    duplicate_rows = set()
    duplicates = count = 0
    content = hashlib.sha256()
    chronology = Counter()
    for _, _, values in rows(path):
        count += 1
        canonical_update(content, values)
        row = dict(zip(columns, values, strict=True))
        row_digest = hashlib.sha256(json.dumps(values, ensure_ascii=False).encode()).digest()
        duplicates += row_digest in duplicate_rows
        duplicate_rows.add(row_digest)
        for c, value in row.items():
            fields[c]["empty"] += value == ""
            fields[c]["whitespace_only"] += value != "" and missing(value)
            fields[c]["distinct"].add(value)
        for key, counts in key_counts.items():
            values_key = tuple(row[c] for c in key)
            key_missing[key] += any(missing(v) for v in values_key)
            counts[values_key] += 1
        parsed = {}
        for c, result in dates.items():
            if missing(row[c]):
                result["missing"] += 1
                continue
            try:
                parsed[c] = timestamp(row[c])
                normalized = parsed[c].isoformat(sep=" ")
                result["min"] = min(result["min"] or normalized, normalized)
                result["max"] = max(result["max"] or normalized, normalized)
            except ValueError:
                result["invalid"] += 1
        purchase = parsed.get("order_purchase_timestamp")
        if purchase:
            for c, value in parsed.items():
                if c != "order_purchase_timestamp" and value < purchase:
                    chronology[f"{c}_before_purchase"] += 1
        for c, result in money.items():
            if missing(row[c]):
                result["missing"] += 1
                continue
            try:
                value = amount(row[c])
                result["sum"] += value
                result["negative"] += value < 0
            except InvalidOperation:
                result["invalid"] += 1
    return {
        "columns": columns,
        "rows": count,
        "content_sha256": content.hexdigest(),
        "exact_duplicate_excess_rows": duplicates,
        "fields": {
            c: {
                "empty": v["empty"],
                "whitespace_only": v["whitespace_only"],
                "missing_rate": (v["empty"] + v["whitespace_only"]) / count if count else None,
                "distinct_including_empty": len(v["distinct"]),
            }
            for c, v in fields.items()
        },
        "keys": {
            ",".join(k): {
                "missing_rows": key_missing[k],
                "duplicate_excess_rows": sum(n - 1 for n in v.values()),
                "duplicated_key_groups": sum(n > 1 for n in v.values()),
                "affected_rows": sum(n for n in v.values() if n > 1),
            }
            for k, v in key_counts.items()
        },
        "timestamps": dates,
        "chronology": dict(chronology),
        "money": {c: {**v, "sum": str(v["sum"])} for c, v in money.items()},
    }


def inspect(source: Path, archive: Path, source_url: str) -> dict:
    paths = sorted(source.glob("*.csv"))
    if not paths:
        raise ValueError(
            "No CSV files found. Follow docs/setup.md to download Olist; no data invented."
        )
    name_map = {name: table for table, name in FILES.items()}
    unexpected = [p.name for p in paths if p.name not in name_map]
    if unexpected:
        raise ValueError(f"Unrecognized CSV files: {unexpected}; inspect and explicitly map first")
    tables = {}
    for path in paths:
        table = name_map[path.name]
        archived, sha = preserve(path, archive)
        tables[table] = {
            "file": path.name,
            "archive_path": str(archived),
            "sha256": sha,
            **profile_file(archived, table),
        }
    relationships = []
    for child, ck, parent, pk, nullable in RELATIONSHIPS:
        check = {
            "child": child,
            "column": ck,
            "parent": parent,
            "parent_column": pk,
            "nullable": nullable,
        }
        if child not in tables or parent not in tables:
            relationships.append({**check, "status": "not_checked_missing_table"})
            continue
        if ck not in tables[child]["columns"] or pk not in tables[parent]["columns"]:
            relationships.append({**check, "status": "not_checked_missing_column"})
            continue
        parent_values = set()
        parent_missing = parent_duplicates = 0
        for cols, _, row in rows(Path(tables[parent]["archive_path"])):
            value = row[cols.index(pk)]
            parent_missing += missing(value)
            parent_duplicates += value in parent_values
            parent_values.add(value)
        orphans = absent = 0
        for cols, _, row in rows(Path(tables[child]["archive_path"])):
            value = row[cols.index(ck)]
            if missing(value):
                absent += 1
            else:
                orphans += value not in parent_values
        relationships.append(
            {
                **check,
                "status": "checked",
                "orphan_rows": orphans,
                "missing_child_rows": absent,
                "parent_missing_rows": parent_missing,
                "parent_duplicate_excess_rows": parent_duplicates,
            }
        )
    identity = {t: v["sha256"] for t, v in sorted(tables.items())}
    snapshot = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {
        "format_version": 1,
        "snapshot_id": snapshot,
        "source_url": source_url,
        "dataset_kind": "historical; source contents not certified by pipeline",
        "missing_tables": sorted(set(FILES) - set(tables)),
        "tables": tables,
        "relationships": relationships,
    }
