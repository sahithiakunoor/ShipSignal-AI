import csv
from pathlib import Path

import pytest

from shipsignal.profile import inspect, profile_file
from shipsignal.source import checksum, rows
from shipsignal.validation import quality_checks


def test_missing_dataset_is_explicit(tmp_path):
    with pytest.raises(ValueError, match="No CSV files"):
        inspect(tmp_path, tmp_path / "archive", "test")


def test_profile_preserves_bytes_and_detects_repeated_grain(manifest, fixture_source):
    assert not manifest["missing_tables"]
    for info in manifest["tables"].values():
        assert checksum(Path(info["archive_path"])) == checksum(fixture_source / info["file"])
    review = manifest["tables"]["reviews"]
    assert review["keys"]["review_id"]["duplicate_excess_rows"] == 1
    assert review["keys"]["order_id"]["duplicate_excess_rows"] == 1
    assert review["fields"]["review_comment_message"]["empty"] == 1
    assert manifest["tables"]["items"]["money"]["price"]["sum"] == "30.30"
    assert all(c["passed"] for c in quality_checks(manifest))


def test_rerun_identity_stable(fixture_source, tmp_path):
    first = inspect(fixture_source, tmp_path / "one", "test")
    second = inspect(fixture_source, tmp_path / "two", "test")
    assert first["snapshot_id"] == second["snapshot_id"]


def test_bad_dates_money_keys_and_whitespace_are_reported(tmp_path):
    path = tmp_path / "bad.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["order_id", "order_item_id", "price", "freight_value", "shipping_limit_date"]
        )
        writer.writerows(
            [["a", "1", "NaN", "-2", "2020-02-30 00:00:00"], ["a", "1", "nonsense", " ", ""]]
        )
    result = profile_file(path, "items")
    assert result["keys"]["order_id,order_item_id"]["duplicate_excess_rows"] == 1
    assert result["timestamps"]["shipping_limit_date"]["invalid"] == 1
    assert result["money"]["price"]["invalid"] == 2
    assert result["money"]["freight_value"]["negative"] == 1
    assert result["fields"]["freight_value"]["whitespace_only"] == 1


@pytest.mark.parametrize("content", ["a,a\n1,2\n", "a,b\n1\n", "a,b\n1,2,3\n", "\n"])
def test_malformed_csv_rejected(tmp_path, content):
    path = tmp_path / "bad.csv"
    path.write_text(content)
    with pytest.raises(ValueError):
        list(rows(path))


def test_relationship_orphans_and_nonunique_parent_detected(fixture_source, tmp_path):
    customer = fixture_source / "olist_customers_dataset.csv"
    with customer.open("a") as handle:
        handle.write("test-customer,test-person,00123\n")
    items = fixture_source / "olist_order_items_dataset.csv"
    items.write_text(items.read_text().replace("test-product", "nonexistent"))
    result = inspect(fixture_source, tmp_path / "archive", "test")
    failures = {c["check"] for c in quality_checks(result) if not c["passed"]}
    assert "orders.customer_id.relationship" in failures
    assert "items.product_id.relationship" in failures


def test_chronology_violations_reported(tmp_path):
    path = tmp_path / "orders.csv"
    path.write_text(
        "order_id,order_purchase_timestamp,order_approved_at\n"
        "x,2020-01-02 00:00:00,2020-01-01 00:00:00\n"
    )
    result = profile_file(path, "orders")
    assert result["chronology"]["order_approved_at_before_purchase"] == 1
