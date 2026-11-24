import copy
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from shipsignal.database import ingest, schema_name, validate_database

pytestmark = pytest.mark.integration


def test_atomic_idempotent_load_and_conservation(database_url, manifest):
    assert ingest(database_url, manifest)["status"] == "loaded"
    assert ingest(database_url, manifest)["status"] == "already_loaded"
    checks = validate_database(database_url, manifest)
    assert all(c["passed"] for c in checks), checks
    with psycopg.connect(database_url) as conn:
        review = conn.execute(
            sql.SQL("SELECT review_comment_message FROM {} WHERE __source_row=1").format(
                sql.Identifier(schema_name(manifest), "reviews")
            )
        ).fetchone()[0]
        assert review == 'Entrega ruim, ação\n"texto"'
        zip_code = conn.execute(
            sql.SQL("SELECT customer_zip_code_prefix FROM {}").format(
                sql.Identifier(schema_name(manifest), "customers")
            )
        ).fetchone()[0]
        assert zip_code == "00123"


def test_failed_load_rolls_back_every_table(database_url, manifest):
    broken = copy.deepcopy(manifest)
    broken["tables"]["reviews"]["rows"] += 1
    with pytest.raises(ValueError, match="source content changed"):
        ingest(database_url, broken)
    with psycopg.connect(database_url) as conn:
        exists = conn.execute(
            "SELECT count(*) FROM pg_namespace WHERE nspname=%s", (schema_name(manifest),)
        ).fetchone()[0]
        assert exists == 0


def test_changed_archive_rejected_before_database_write(database_url, manifest):
    Path(manifest["tables"]["orders"]["archive_path"]).write_text("modified")
    with pytest.raises(ValueError, match="archive does not match"):
        ingest(database_url, manifest)


def test_database_tampering_is_detected(database_url, manifest):
    ingest(database_url, manifest)
    with psycopg.connect(database_url) as conn:
        conn.execute(
            sql.SQL("UPDATE {} SET price='999' WHERE __source_row=1").format(
                sql.Identifier(schema_name(manifest), "items")
            )
        )
    failed = {c["check"] for c in validate_database(database_url, manifest) if not c["passed"]}
    assert "items.all_field_content" in failed
    assert "items.price.sum" in failed
    assert "order_grain_join.count_and_monetary_conservation" in failed


def test_nonnumeric_database_edit_is_a_finding_not_a_cast_crash(database_url, manifest):
    ingest(database_url, manifest)
    with psycopg.connect(database_url) as conn:
        conn.execute(
            sql.SQL("UPDATE {} SET price='invalid' WHERE __source_row=1").format(
                sql.Identifier(schema_name(manifest), "items")
            )
        )
    checks = validate_database(database_url, manifest)
    failed = {c["check"] for c in checks if not c["passed"]}
    assert "items.all_field_content" in failed
    assert "items.price.sum" in failed
    assert "order_grain_join.count_and_monetary_conservation" in failed
