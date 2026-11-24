"""Synthetic software fixtures. Assert grain and denominators against independent SQL."""

import csv
from datetime import date

import pytest
from fastapi.testclient import TestClient

from shipsignal.analytics import build, connect, overview
from shipsignal.api.main import app
from shipsignal.database import ingest
from shipsignal.profile import inspect


@pytest.fixture
def analytical_source(fixture_source, tmp_path):
    path = fixture_source / "olist_orders_dataset.csv"
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames + ["order_status"]
    for i, row in enumerate(rows):
        row.update(
            order_status="delivered",
            order_approved_at=row["order_purchase_timestamp"],
            order_delivered_customer_date="2020-01-10 10:00:00"
            if i == 0
            else "2020-01-03 10:00:00",
            order_estimated_delivery_date="2020-01-05 10:00:00",
        )
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    path = fixture_source / "olist_customers_dataset.csv"
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames + ["customer_state", "customer_city"]
    for row in rows:
        row.update(customer_state="SP", customer_city="test-city")
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return inspect(
        fixture_source, tmp_path / "analytical_archive", "synthetic-software-test-fixtures"
    )


@pytest.mark.integration
def test_order_grain_filters_and_api(database_url, analytical_source, monkeypatch):
    ingest(database_url, analytical_source)
    result = build(database_url, analytical_source)
    assert result["orders"] == 2
    report = overview(database_url)
    assert report["kpis"]["orders"] == 2
    assert report["kpis"]["late_orders"] == 1
    assert report["kpis"]["late_delivery_rate"] == 0.5
    assert report["kpis"]["average_delivery_days"] == 5
    assert sum(r["orders"] for r in report["monthly"]) == 2
    assert sum(r["orders"] for r in report["regions"]) == 2
    assert overview(database_url, state="RJ")["kpis"]["late_delivery_rate"] is None
    assert overview(database_url, start=date(2020, 1, 2))["kpis"]["orders"] == 1
    with connect(database_url) as conn:
        # Multi-item/payment/review fixture must not multiply monetary values.
        row = conn.execute(
            "SELECT sum(item_value) item,sum(payment_value) payment FROM analytics.order_fact"
        ).fetchone()
        assert str(row["item"]) == "30.30"
        assert str(row["payment"]) == "33.80"
    monkeypatch.setenv("DATABASE_URL", database_url)
    client = TestClient(app)
    response = client.get("/api/analytics?state=SP")
    assert response.status_code == 200
    assert response.json()["kpis"]["orders"] == 2
    assert client.get("/api/analytics?state=SP%27%3BDROP").status_code == 422
    assert client.get("/api/analytics?start=2020-02-01&end=2020-01-01").status_code == 422


def test_missing_database_error_is_actionable(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = TestClient(app).get("/api/analytics")
    assert response.status_code == 503
    assert "DATABASE_URL" in response.json()["detail"]


@pytest.mark.integration
def test_same_exception_counts_do_not_waive_different_categories(
    database_url, analytical_source, fixture_source, tmp_path
):
    path = fixture_source / "olist_products_dataset.csv"
    with path.open("a", newline="") as handle:
        writer = csv.writer(handle)
        for i in range(13):
            writer.writerow([f"test-unmapped-{i}", "test-unreviewed-category"])
        for i in range(610):
            writer.writerow([f"test-blank-{i}", ""])
    manifest = inspect(
        fixture_source, tmp_path / "unreviewed_archive", "synthetic-software-test-fixtures"
    )
    ingest(database_url, manifest)
    with pytest.raises(ValueError, match="categories differ"):
        build(database_url, manifest)
