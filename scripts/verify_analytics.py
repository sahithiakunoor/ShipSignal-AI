"""Independently recompute every displayed analytical aggregate from the original CSVs."""

import json
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
orders = pd.read_csv(root / "data/raw/olist_orders_dataset.csv", dtype=str, keep_default_na=False)
customers = pd.read_csv(
    root / "data/raw/olist_customers_dataset.csv", dtype=str, keep_default_na=False
)
assert orders.order_id.is_unique and customers.customer_id.is_unique
frame = orders.merge(
    customers[["customer_id", "customer_state"]],
    on="customer_id",
    how="left",
    validate="many_to_one",
)
for c in [
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]:
    frame[c] = pd.to_datetime(frame[c], errors="coerce")
purchase = frame.order_purchase_timestamp
actual = frame.order_delivered_customer_date
promise = frame.order_estimated_delivery_date
frame["eligible"] = (
    (frame.order_status == "delivered")
    & purchase.notna()
    & actual.notna()
    & promise.notna()
    & (actual >= purchase)
    & (promise >= purchase)
)
frame["late"] = frame.eligible & (actual > promise)
frame["duration"] = ((actual - purchase).dt.total_seconds() / 86400).where(frame.eligible)
frame["lateness"] = ((actual - promise).dt.total_seconds() / 86400).where(frame.late)
frame["month"] = purchase.dt.strftime("%Y-%m")


def compare(group, result):
    assert result["orders"] == len(group)
    assert result["eligible_delivered_orders"] == int(group.eligible.sum())
    assert result["excluded_orders"] == int((~group.eligible).sum())
    assert result["late_orders"] == int(group.late.sum())
    expected = {
        "late_delivery_rate": group.loc[group.eligible, "late"].mean(),
        "average_delivery_days": group.duration.mean(),
        "median_delivery_days": (
            group.duration.dropna().median() if group.duration.notna().any() else np.nan
        ),
        "average_late_days": group.lateness.mean(),
    }
    for name, value in expected.items():
        if pd.isna(value):
            assert result[name] is None
        else:
            np.testing.assert_allclose(result[name], float(value), rtol=1e-10, atol=1e-10)


client = httpx.Client(base_url="http://127.0.0.1:8787", timeout=30, trust_env=False)
response = client.get("/api/analytics")
response.raise_for_status()
report = response.json()
compare(frame, report["kpis"])
assert report["coverage"]["start"] == str(purchase.min().date())
assert report["coverage"]["end"] == str(purchase.max().date())
for r in report["monthly"]:
    compare(frame.loc[frame.month == r["month"]], r)
for r in report["regions"]:
    compare(frame.loc[frame.customer_state == r["state"]], r)
assert sum(r["orders"] for r in report["monthly"]) == len(frame)
assert sum(r["orders"] for r in report["regions"]) == len(frame)
assert {
    r["status"]: r["orders"] for r in report["statuses"]
} == frame.order_status.value_counts().to_dict()
for state in ["SP", "RJ", "AM"]:
    r = client.get("/api/analytics", params={"state": state}).json()
    compare(frame.loc[frame.customer_state == state], r["kpis"])
scoped = frame.loc[
    (purchase >= "2018-01-01") & (purchase < "2018-03-01") & (frame.customer_state == "SP")
]
r = client.get(
    "/api/analytics", params={"state": "SP", "start": "2018-01-01", "end": "2018-02-28"}
).json()
compare(scoped, r["kpis"])
result = {
    "passed": True,
    "snapshot_id": report["snapshot_id"],
    "kpis": report["kpis"],
    "regional_groups_verified": len(report["regions"]),
    "monthly_groups_verified": len(report["monthly"]),
    "checks": [
        "original_csv_vs_all_kpis",
        "date_coverage",
        "all_monthly_aggregates",
        "all_regional_aggregates",
        "all_status_counts",
        "state_filters",
        "combined_date_and_state_filter",
    ],
}
(root / "reports/analytics_verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
