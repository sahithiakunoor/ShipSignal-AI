"""Recompute saved test predictions and metrics; compare API artifacts to actual model output."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from psycopg import sql

from shipsignal.analytics import connect, dataset
from shipsignal.ml import (
    FEATURE_SQL,
    FEATURES,
    NUMERIC,
    chronological_split,
    feature_frame,
    metrics,
    probability,
)
from shipsignal.settings import Settings

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
s = Settings.read()
report = json.loads((s.artifacts / "ml/evaluation.json").read_text())
with connect(s.database_url) as conn:
    active = dataset(conn)
    rows = conn.execute(
        sql.SQL(FEATURE_SQL).format(
            **{t: sql.Identifier(active["raw_schema"], t) for t in ["items", "products", "sellers"]}
        )
    ).fetchall()
data = feature_frame(pd.DataFrame(rows))
data["is_late"] = data.is_late.astype(int)
splits, audit = chronological_split(data)
bundle = joblib.load(s.artifacts / "ml" / f"{report['selected_model']}.joblib")
assert list(bundle["pipeline"].feature_names_in_) == FEATURES
actual_medians = splits["train"][NUMERIC].median().fillna(0).values
stored = (
    bundle["pipeline"]
    .named_steps["preprocess"]
    .named_transformers_["numeric"]
    .named_steps["impute"]
    .statistics_
)
np.testing.assert_allclose(stored, actual_medians)
test = splits["test"]
pred = probability(bundle, test)
saved = pd.read_csv(s.artifacts / "ml/test_predictions.csv", dtype={"order_id": str})
assert saved.order_id.tolist() == test.order_id.tolist()
np.testing.assert_allclose(saved.late_probability, pred, rtol=1e-6, atol=1e-8)
actual = metrics(test.is_late, pred, bundle["threshold"])
for key in ["precision", "recall", "f1", "roc_auc", "pr_auc_average_precision", "brier_score"]:
    assert abs(actual[key] - report["candidates"][report["selected_model"]]["test"][key]) < 1e-12
assert sum(b["orders"] for b in actual["calibration"]) == len(test)
result = {
    "passed": True,
    "model_id": report["model_id"],
    "test_orders": len(test),
    "checks": [
        "train_only_imputation",
        "feature_allowlist",
        "prediction_replay",
        "saved_order_identity",
        "metric_recalculation",
        "calibration_counts",
    ],
}
Path("reports/ml_verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
