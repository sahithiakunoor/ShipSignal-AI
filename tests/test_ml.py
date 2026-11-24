"""Synthetic chronology and metric tests, not claimed Olist model results."""

import numpy as np
import pandas as pd

from shipsignal.ml import (
    CATEGORICAL,
    EXCLUDED,
    FEATURES,
    NUMERIC,
    chronological_split,
    feature_frame,
    metrics,
)


def test_features_exclude_outcomes_and_keep_prediction_time_transformations():
    assert not set(FEATURES) & EXCLUDED
    record = {k: 1 for k in NUMERIC}
    record.update({k: "test" for k in CATEGORICAL})
    record.update(purchased_at="2020-01-01 10:00:00", approved_at="2020-01-01 12:00:00")
    result = feature_frame(pd.DataFrame([record]))
    assert result.approval_wait_hours.iloc[0] == 2
    assert result.purchase_hour.iloc[0] == 10
    assert result.approval_hour.iloc[0] == 12


def test_chronological_boundaries_and_label_maturity():
    n = 1000
    approved = pd.date_range("2020-01-01", periods=n, freq="h")
    frame = pd.DataFrame(
        {
            "order_id": [str(i) for i in range(n)],
            "approved_at": approved,
            "delivered_at": pd.date_range("2020-01-02 06:00:00", periods=n, freq="h"),
            "is_late": np.arange(n) % 2,
        }
    )
    splits, audit = chronological_split(frame)
    assert splits["train"].approved_at.max() < splits["calibration"].approved_at.min()
    assert splits["calibration"].approved_at.max() < splits["selection"].approved_at.min()
    assert splits["selection"].approved_at.max() < splits["test"].approved_at.min()
    assert splits["train"].delivered_at.max() < pd.Timestamp(
        audit["boundaries"]["validation_start"]
    )
    assert splits["calibration"].delivered_at.max() < pd.Timestamp(
        audit["boundaries"]["selection_start"]
    )
    assert splits["selection"].delivered_at.max() < pd.Timestamp(audit["boundaries"]["test_start"])
    assert audit["periods"]["train"]["purged_unmatured_labels"] > 0


def test_metric_definition_and_calibration_counts():
    result = metrics([0, 1, 0, 1], [0.1, 0.9, 0.2, 0.8], 0.5)
    assert result["f1"] == 1
    assert result["roc_auc"] == 1
    assert result["pr_auc_average_precision"] == 1
    assert sum(b["orders"] for b in result["calibration"]) == 4
