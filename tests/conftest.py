"""SYNTHETIC SOFTWARE TEST FIXTURES ONLY. These are not Olist records or results."""

import csv
import os
import uuid

import psycopg
import pytest
from psycopg import sql

from shipsignal.contracts import FILES
from shipsignal.profile import inspect


@pytest.fixture
def fixture_source(tmp_path):
    source = tmp_path / "synthetic"
    source.mkdir()
    tables = {
        "orders": (
            [
                "order_id",
                "customer_id",
                "order_purchase_timestamp",
                "order_approved_at",
                "order_delivered_carrier_date",
                "order_delivered_customer_date",
                "order_estimated_delivery_date",
            ],
            [
                ["test-order-a", "test-customer", "2020-01-01 10:00:00", "", "", "", ""],
                ["test-order-b", "test-customer", "2020-01-02 10:00:00", "", "", "", ""],
            ],
        ),
        "items": (
            [
                "order_id",
                "order_item_id",
                "product_id",
                "seller_id",
                "price",
                "freight_value",
                "shipping_limit_date",
            ],
            [
                ["test-order-a", "1", "test-product", "test-seller", "10.10", "1.20", ""],
                ["test-order-a", "2", "test-product", "test-seller", "20.20", "2.30", ""],
            ],
        ),
        "payments": (
            ["order_id", "payment_sequential", "payment_value"],
            [["test-order-a", "1", "20.00"], ["test-order-a", "2", "13.80"]],
        ),
        "reviews": (
            [
                "review_id",
                "order_id",
                "review_comment_message",
                "review_creation_date",
                "review_answer_timestamp",
            ],
            [
                ["test-review", "test-order-a", 'Entrega ruim, ação\n"texto"', "", ""],
                ["test-review", "test-order-a", "", "", ""],
            ],
        ),
        "customers": (
            ["customer_id", "customer_unique_id", "customer_zip_code_prefix"],
            [["test-customer", "test-person", "00123"]],
        ),
        "sellers": (["seller_id"], [["test-seller"]]),
        "products": (["product_id", "product_category_name"], [["test-product", "test-category"]]),
        "geolocation": (["geolocation_zip_code_prefix"], [["00123"], ["00123"]]),
        "category_translation": (
            ["product_category_name", "product_category_name_english"],
            [["test-category", "test category"]],
        ),
    }
    for table, (columns, values) in tables.items():
        with (source / FILES[table]).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(values)
    return source


@pytest.fixture
def manifest(fixture_source, tmp_path):
    return inspect(fixture_source, tmp_path / "archive", "synthetic-software-test-fixtures")


@pytest.fixture
def database_url():
    base = os.environ.get("TEST_DATABASE_URL")
    if not base:
        pytest.skip("Set TEST_DATABASE_URL to run real PostgreSQL integration tests")
    name = "shipsignal_test_" + uuid.uuid4().hex
    # Isolate every integration test in a disposable database, never truncate user tables.
    with psycopg.connect(base, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    params = psycopg.conninfo.conninfo_to_dict(base)
    params["dbname"] = name
    try:
        yield psycopg.conninfo.make_conninfo(**params)
    finally:
        with psycopg.connect(base, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
