"""Transactional, immutable-per-snapshot raw loads. No destructive reload command."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from .contracts import FILES, MONEY
from .source import canonical_update, checksum, headers, rows


def schema_name(manifest):
    digest = manifest["snapshot_id"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid snapshot identifier")
    return "raw_" + digest[:20]


def verify_sources(manifest):
    if manifest.get("format_version") != 1 or not manifest.get("tables"):
        raise ValueError("Unsupported or empty manifest")
    if not set(manifest["tables"]) <= set(FILES):
        raise ValueError("Unrecognized table in manifest")
    identity = {t: v["sha256"] for t, v in sorted(manifest["tables"].items())}
    expected = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    if expected != manifest["snapshot_id"]:
        raise ValueError("Snapshot identity does not match source checksums")
    for table, info in manifest["tables"].items():
        path = Path(info["archive_path"])
        if checksum(path) != info["sha256"] or headers(path) != info["columns"]:
            raise ValueError(f"{table}: archive does not match inspected manifest")


def ingest(dsn, manifest):
    verify_sources(manifest)
    schema = schema_name(manifest)
    with psycopg.connect(dsn) as conn:
        # One transaction includes schema, every table, and metadata. Any error rolls back all.
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (schema,))
        conn.execute("CREATE SCHEMA IF NOT EXISTS ingestion")
        conn.execute("""CREATE TABLE IF NOT EXISTS ingestion.snapshots (
            snapshot_id text PRIMARY KEY, raw_schema text UNIQUE NOT NULL,
            loaded_at timestamptz NOT NULL DEFAULT now(), manifest jsonb NOT NULL)""")
        previous = conn.execute(
            "SELECT snapshot_id FROM ingestion.snapshots WHERE raw_schema = %s", (schema,)
        ).fetchone()
        if previous:
            if previous[0] != manifest["snapshot_id"]:
                raise ValueError("Snapshot schema hash collision")
            return {"status": "already_loaded", "schema": schema}
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        for table, info in manifest["tables"].items():
            column_defs = [sql.SQL("__source_row bigint PRIMARY KEY")]
            column_defs += [
                sql.SQL("{} text NOT NULL").format(sql.Identifier(c)) for c in info["columns"]
            ]
            target = sql.Identifier(schema, table)
            conn.execute(
                sql.SQL("CREATE TABLE {} ({})").format(target, sql.SQL(", ").join(column_defs))
            )
            digest = hashlib.sha256()
            count = 0
            with conn.cursor().copy(sql.SQL("COPY {} FROM STDIN").format(target)) as copy:
                for _, number, values in rows(Path(info["archive_path"])):
                    copy.write_row([number, *values])
                    canonical_update(digest, values)
                    count += 1
            if count != info["rows"] or digest.hexdigest() != info["content_sha256"]:
                raise ValueError(f"{table}: source content changed since inspection")
        verify_sources(manifest)
        conn.execute(
            """INSERT INTO ingestion.snapshots(snapshot_id, raw_schema, manifest)
                     VALUES (%s, %s, %s)""",
            (manifest["snapshot_id"], schema, Jsonb(manifest)),
        )
    return {"status": "loaded", "schema": schema}


def validate_database(dsn, manifest):
    verify_sources(manifest)
    schema = schema_name(manifest)
    checks = []
    with psycopg.connect(dsn) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        stored = conn.execute(
            "SELECT snapshot_id FROM ingestion.snapshots WHERE raw_schema = %s", (schema,)
        ).fetchone()
        if not stored or stored[0] != manifest["snapshot_id"]:
            raise ValueError("Snapshot has not been ingested")
        for table, info in manifest["tables"].items():
            target = sql.Identifier(schema, table)
            total = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(target)).fetchone()[0]
            checks.append(
                {
                    "check": f"{table}.row_count",
                    "passed": total == info["rows"],
                    "expected": info["rows"],
                    "actual": total,
                }
            )
            digest = hashlib.sha256()
            with conn.cursor(name=f"verify_{table}") as cursor:
                cursor.execute(
                    sql.SQL("SELECT {} FROM {} ORDER BY __source_row").format(
                        sql.SQL(",").join(map(sql.Identifier, info["columns"])), target
                    )
                )
                for row in cursor:
                    canonical_update(digest, list(row))
            content_matches = digest.hexdigest() == info["content_sha256"]
            checks.append(
                {
                    "check": f"{table}.all_field_content",
                    "passed": content_matches,
                }
            )
            for column in MONEY.get(table, []):
                profile = info["money"].get(column)
                if profile is None or profile["invalid"] or not content_matches:
                    checks.append(
                        {
                            "check": f"{table}.{column}.sum",
                            "passed": False,
                            "reason": "missing/invalid numeric source or database content mismatch",
                        }
                    )
                    continue
                value = conn.execute(
                    sql.SQL(
                        "SELECT coalesce(sum(nullif(btrim({}), '')::numeric), 0) FROM {}"
                    ).format(sql.Identifier(column), target)
                ).fetchone()[0]
                checks.append(
                    {
                        "check": f"{table}.{column}.sum",
                        "passed": value == Decimal(profile["sum"]),
                        "expected": profile["sum"],
                        "actual": str(value),
                    }
                )
        # Demonstrate the safe join pattern without imposing an unverified review business key.
        required = {
            "orders": ["order_id"],
            "items": ["order_id", "price", "freight_value"],
            "payments": ["order_id", "payment_value"],
            "reviews": ["order_id"],
        }
        available = all(
            t in manifest["tables"] and set(cols) <= set(manifest["tables"][t]["columns"])
            for t, cols in required.items()
        )
        valid_money = all(
            not p["invalid"]
            for t in ("items", "payments")
            for p in manifest["tables"].get(t, {}).get("money", {}).values()
        )
        content_verified = all(
            c["passed"] for c in checks if c["check"].endswith(".all_field_content")
        )
        if available and valid_money and content_verified:
            result = conn.execute(
                sql.SQL("""
                WITH i AS (
                    SELECT order_id, sum(nullif(btrim(price), '')::numeric) AS price,
                           sum(nullif(btrim(freight_value), '')::numeric) AS freight
                    FROM {items} GROUP BY order_id
                ), p AS (
                    SELECT order_id, sum(nullif(btrim(payment_value), '')::numeric) AS payment
                    FROM {payments} GROUP BY order_id
                ), r AS (SELECT order_id, count(*) AS reviews FROM {reviews} GROUP BY order_id)
                SELECT count(*), coalesce(sum(i.price), 0), coalesce(sum(i.freight), 0),
                       coalesce(sum(p.payment), 0)
                FROM {orders} o LEFT JOIN i USING (order_id)
                LEFT JOIN p USING (order_id) LEFT JOIN r USING (order_id)
            """).format(**{t: sql.Identifier(schema, t) for t in required})
            ).fetchone()
            expected = [
                manifest["tables"]["orders"]["rows"],
                manifest["tables"]["items"]["money"]["price"]["sum"],
                manifest["tables"]["items"]["money"]["freight_value"]["sum"],
                manifest["tables"]["payments"]["money"]["payment_value"]["sum"],
            ]
            checks.append(
                {
                    "check": "order_grain_join.count_and_monetary_conservation",
                    "passed": list(result) == [Decimal(str(v)) for v in expected],
                    "expected": [str(v) for v in expected],
                    "actual": [str(v) for v in result],
                }
            )
        else:
            checks.append(
                {
                    "check": "order_grain_join.count_and_monetary_conservation",
                    "passed": False,
                    "reason": "required columns absent or money invalid",
                }
            )
    return checks
