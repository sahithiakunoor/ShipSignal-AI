"""Approval-time, chronology-preserving late-delivery training and saved-risk exploration."""

import hashlib
import json
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from psycopg import sql
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from .analytics import connect, dataset
from .settings import NotReady, Settings

NUMERIC = [
    "item_count",
    "seller_count",
    "category_count",
    "item_value",
    "freight_value",
    "weight_g",
    "length_cm",
    "height_cm",
    "width_cm",
    "approval_wait_hours",
    "purchase_month",
    "purchase_weekday",
    "purchase_hour",
    "approval_month",
    "approval_weekday",
    "approval_hour",
]
CATEGORICAL = ["customer_state", "seller_states", "category"]
FEATURES = NUMERIC + CATEGORICAL
EXCLUDED = {
    "delivered_at",
    "estimated_at",
    "order_status",
    "is_late",
    "review_score",
    "review_comment_message",
    "payment_value",
    "shipping_limit_date",
    "order_id",
    "customer_id",
    "approved_at",
    "purchased_at",
}
MODEL_VERSION = "approval_v1"

FEATURE_SQL = """
WITH enriched AS (
 SELECT i.order_id, i.order_item_id,
  coalesce(nullif(p.product_category_name,''),'unknown') category,
  nullif(p.product_weight_g,'')::float weight_g,
  nullif(p.product_length_cm,'')::float length_cm,
  nullif(p.product_height_cm,'')::float height_cm,
  nullif(p.product_width_cm,'')::float width_cm,
  s.seller_state
 FROM {items} i LEFT JOIN {products} p USING(product_id) LEFT JOIN {sellers} s USING(seller_id)
), agg AS (
 SELECT order_id,count(DISTINCT category)::int category_count,
  string_agg(DISTINCT seller_state,',' ORDER BY seller_state) seller_states,
  avg(weight_g) weight_g,avg(length_cm) length_cm,avg(height_cm) height_cm,avg(width_cm) width_cm
 FROM enriched GROUP BY order_id
), ranks AS (
 SELECT order_id,category,row_number() OVER(PARTITION BY order_id ORDER BY count(*) DESC,category) rank
 FROM enriched GROUP BY order_id,category
)
SELECT f.*, a.category_count,a.seller_states,a.weight_g,a.length_cm,a.height_cm,a.width_cm,r.category
FROM analytics.order_fact f LEFT JOIN agg a USING(order_id)
LEFT JOIN ranks r ON r.order_id=f.order_id AND r.rank=1
WHERE f.eligible_delivery AND f.approved_at IS NOT NULL
 AND f.approved_at>=f.purchased_at AND f.delivered_at>=f.approved_at
ORDER BY f.approved_at,f.order_id
"""


def feature_frame(frame):
    frame = frame.copy()
    for name in ["purchased_at", "approved_at", "delivered_at", "estimated_at"]:
        if name in frame:
            frame[name] = pd.to_datetime(frame[name])
    frame["approval_wait_hours"] = (
        frame.approved_at - frame.purchased_at
    ).dt.total_seconds() / 3600
    for prefix, column in [("purchase", "purchased_at"), ("approval", "approved_at")]:
        frame[prefix + "_month"] = frame[column].dt.month
        frame[prefix + "_weekday"] = frame[column].dt.dayofweek
        frame[prefix + "_hour"] = frame[column].dt.hour
    for col in NUMERIC:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in CATEGORICAL:
        frame[col] = frame[col].fillna("unknown").astype(str)
    assert not (set(FEATURES) & EXCLUDED)
    return frame


def chronological_split(frame):
    frame = frame.sort_values(["approved_at", "order_id"]).reset_index(drop=True)
    if len(frame) < 200:
        raise ValueError("Too few eligible real records for temporal evaluation.")
    times = frame.approved_at
    boundaries = [times.iloc[int(len(frame) * q)] for q in (0.6, 0.7, 0.8)]
    a, b, c = boundaries
    if not a < b < c:
        raise ValueError("Temporal boundaries are not distinct.")
    masks = [times < a, (times >= a) & (times < b), (times >= b) & (times < c), times >= c]
    cutoffs = [a, b, c, None]
    splits = {}
    audit = {
        "boundaries": {"validation_start": str(a), "selection_start": str(b), "test_start": str(c)},
        "periods": {},
    }
    for name, mask, cutoff in zip(
        ["train", "calibration", "selection", "test"], masks, cutoffs, strict=True
    ):
        original = frame.loc[mask]
        eligible = original if cutoff is None else original.loc[original.delivered_at < cutoff]
        if len(eligible) < 50 or eligible.is_late.nunique() != 2:
            raise ValueError("A chronological cohort is too small or lacks both target classes.")
        splits[name] = eligible.copy()
        audit["periods"][name] = {
            "orders": len(eligible),
            "purged_unmatured_labels": len(original) - len(eligible),
            "approval_start": str(eligible.approved_at.min()),
            "approval_end": str(eligible.approved_at.max()),
            "latest_label_observed": str(eligible.delivered_at.max()),
            "late_prevalence": float(eligible.is_late.mean()),
        }
    return splits, audit


def logit(probabilities):
    p = np.clip(probabilities, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


def probability(bundle, frame):
    raw = bundle["pipeline"].predict_proba(frame[FEATURES])[:, 1]
    return bundle["calibrator"].predict_proba(logit(raw))[:, 1]


def metrics(y, p, threshold):
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    pred = p >= threshold
    top = np.argsort(-p, kind="stable")[: max(1, int(np.ceil(len(p) * 0.1)))]
    bins = []
    for low in np.linspace(0, 0.9, 10):
        mask = (p >= low) & ((p < low + 0.1) if low < 0.9 else (p <= 1))
        if mask.any():
            bins.append(
                {
                    "mean_probability": float(p[mask].mean()),
                    "observed_rate": float(y[mask].mean()),
                    "orders": int(mask.sum()),
                }
            )
    return {
        "orders": len(y),
        "prevalence": float(y.mean()),
        "threshold": float(threshold),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc_average_precision": float(average_precision_score(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "precision_top_10pct": float(y[top].mean()),
        "recall_top_10pct": float(y[top].sum() / max(1, y.sum())),
        "calibration": bins,
    }


def train():
    settings = Settings.read()
    with connect(settings.database_url) as conn:
        active = dataset(conn)
        rows = conn.execute(
            sql.SQL(FEATURE_SQL).format(
                **{
                    t: sql.Identifier(active["raw_schema"], t)
                    for t in ["items", "products", "sellers"]
                }
            )
        ).fetchall()
    data = feature_frame(pd.DataFrame(rows))
    data["is_late"] = data.is_late.astype(int)
    splits, audit = chronological_split(data)
    tr, cal, selection, test = (splits[n] for n in ["train", "calibration", "selection", "test"])
    candidates = {
        "logistic_regression": LogisticRegression(
            max_iter=1500, C=0.5, class_weight="balanced", random_state=42
        ),
        "xgboost": XGBClassifier(
            n_estimators=180,
            max_depth=4,
            learning_rate=0.05,
            min_child_weight=20,
            subsample=0.85,
            colsample_bytree=0.9,
            reg_lambda=10,
            tree_method="hist",
            device="cpu",
            n_jobs=4,
            eval_metric="logloss",
            random_state=42,
            scale_pos_weight=float((1 - tr.is_late.mean()) / tr.is_late.mean()),
        ),
    }
    bundles = {}
    evaluation = {}
    for name, estimator in candidates.items():
        numeric = Pipeline(
            [
                ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scale", StandardScaler()),
            ]
        )
        categorical = Pipeline(
            [
                ("impute", SimpleImputer(strategy="constant", fill_value="unknown")),
                (
                    "onehot",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        min_frequency=20,
                        max_categories=50,
                        sparse_output=False,
                    ),
                ),
            ]
        )
        prep = ColumnTransformer(
            [("numeric", numeric, NUMERIC), ("categorical", categorical, CATEGORICAL)]
        )
        pipeline = Pipeline([("preprocess", prep), ("classifier", estimator)])
        pipeline.fit(tr[FEATURES], tr.is_late)
        raw = pipeline.predict_proba(cal[FEATURES])[:, 1]
        calibrator = LogisticRegression(C=1e6, random_state=42).fit(logit(raw), cal.is_late)
        bundle = {"pipeline": pipeline, "calibrator": calibrator}
        val_p = probability(bundle, selection)
        # Prespecified threshold grid and validation-only maximum-F1 choice.
        thresholds = np.linspace(0.02, 0.8, 157)
        threshold = float(
            max(thresholds, key=lambda t: f1_score(selection.is_late, val_p >= t, zero_division=0))
        )
        evaluation[name] = {"validation": metrics(selection.is_late, val_p, threshold)}
        bundle["threshold"] = threshold
        bundles[name] = bundle
    chosen = max(evaluation, key=lambda n: evaluation[n]["validation"]["pr_auc_average_precision"])
    # Choices above are fixed before any test evaluation.
    for name, bundle in bundles.items():
        test_p = probability(bundle, test)
        evaluation[name]["test"] = metrics(test.is_late, test_p, bundle["threshold"])
    baseline_p = np.repeat(float(tr.is_late.mean()), len(test))
    baseline = metrics(test.is_late, baseline_p, 0.5)
    identity = {
        "snapshot_id": active["snapshot_id"],
        "version": MODEL_VERSION,
        "features": FEATURES,
        "boundaries": audit["boundaries"],
        "selected_model": chosen,
    }
    model_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    report = {
        **identity,
        "model_id": model_id,
        "created_at": datetime.now(UTC).isoformat(),
        "cohort": "Observed delivered outcomes only; approval-time historical prediction.",
        "operational_readiness": "Experimental; inspect held-out metrics before any operational use.",
        "feature_availability_document": "docs/feature_availability.md",
        "split_audit": audit,
        "selection_rule": "Highest average precision on later validation; threshold maximizes validation F1.",
        "candidates": evaluation,
        "prevalence_baseline": baseline,
        "limitations": [
            "Catalog/seller attributes treated as static; source is not event-versioned.",
            "Delivery promise excluded as an input; actual outcome/promise used only for label/cohort.",
            "Temporal shifts can impair performance. No causal interpretation.",
            "No performance claim for canceled, undelivered or future live orders.",
        ],
    }
    dest = settings.artifacts / "ml"
    dest.mkdir(parents=True, exist_ok=True)
    for name, bundle in bundles.items():
        bundle.update(
            model_id=model_id, snapshot_id=active["snapshot_id"], name=name, features=FEATURES
        )
        joblib.dump(bundle, dest / (name + ".joblib"))
    selected = bundles[chosen]
    p = probability(selected, test)
    saved = test[
        ["order_id", "approved_at", "customer_state", "delivered_at", "estimated_at", "is_late"]
    ].copy()
    saved["late_probability"] = p
    saved["flagged"] = p >= selected["threshold"]
    saved["cohort"] = "test"
    saved["model_id"] = model_id
    saved["snapshot_id"] = active["snapshot_id"]
    saved.to_csv(dest / "test_predictions.csv", index=False)
    (dest / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    (dest / "feature_contract.json").write_text(
        json.dumps({"features": FEATURES, "excluded": sorted(EXCLUDED)}, indent=2)
    )
    return report


def load_report(settings=None):
    settings = settings or Settings.read()
    path = settings.artifacts / "ml/evaluation.json"
    if not path.exists():
        raise NotReady("Train real-data models with python -m shipsignal.tasks train first.")
    report = json.loads(path.read_text())
    with connect(settings.database_url) as conn:
        if dataset(conn)["snapshot_id"] != report["snapshot_id"]:
            raise NotReady("Model artifacts belong to a different dataset snapshot. Retrain.")
    return report


def risks(state=None, minimum=0.0, limit=50, offset=0, start=None, end=None, order_id=None):
    settings = Settings.read()
    report = load_report(settings)
    frame = pd.read_csv(settings.artifacts / "ml/test_predictions.csv", dtype={"order_id": str})
    if state:
        frame = frame.loc[frame.customer_state == state]
    # Dashboard filters consistently use purchase cohorts; resolve IDs from typed order facts.
    if start or end:
        from .analytics import where

        clause, params = where(start, end, state)
        with connect(settings.database_url) as conn:
            allowed = {
                r["order_id"]
                for r in conn.execute("SELECT order_id FROM analytics.order_fact" + clause, params)
            }
        frame = frame.loc[frame.order_id.isin(allowed)]
    if order_id:
        frame = frame.loc[frame.order_id == order_id]
    frame = frame.loc[frame.late_probability >= minimum].sort_values(
        ["late_probability", "order_id"], ascending=[False, True]
    )
    total = len(frame)
    items = frame.iloc[offset : offset + limit].to_dict(orient="records")
    return {
        "report": report,
        "total": total,
        "items": items,
        "offset": offset,
        "limit": limit,
        "query_id": "saved_test_predictions_v1",
        "historical": True,
    }


def recompute(order_id):
    """Replay the selected model on one held-out order's approval-time feature snapshot."""
    settings = Settings.read()
    report = load_report(settings)
    saved = pd.read_csv(settings.artifacts / "ml/test_predictions.csv", dtype={"order_id": str})
    match = saved.loc[saved.order_id == order_id]
    if match.empty:
        return None
    # Only trusted locally trained joblib artifacts are accepted; request values never select a path.
    bundle = joblib.load(settings.artifacts / "ml" / f"{report['selected_model']}.joblib")
    if bundle["snapshot_id"] != report["snapshot_id"] or bundle["model_id"] != report["model_id"]:
        raise NotReady("Model artifact provenance mismatch; retrain before scoring.")
    with connect(settings.database_url) as conn:
        active = dataset(conn)
        query = sql.SQL(
            "SELECT * FROM (" + FEATURE_SQL + ") approved_features WHERE order_id=%s"
        ).format(
            **{t: sql.Identifier(active["raw_schema"], t) for t in ["items", "products", "sellers"]}
        )
        rows = conn.execute(query, (order_id,)).fetchall()
    if len(rows) != 1:
        raise NotReady("A unique eligible source order could not be reconstructed.")
    frame = feature_frame(pd.DataFrame(rows))
    p = float(probability(bundle, frame)[0])
    values = {}
    for feature in FEATURES:
        value = frame[feature].iloc[0]
        values[feature] = (
            None if pd.isna(value) else (value.item() if isinstance(value, np.generic) else value)
        )
    return {
        "order_id": order_id,
        "late_probability": p,
        "threshold": float(bundle["threshold"]),
        "flagged": p >= bundle["threshold"],
        "saved_late_probability": float(match.late_probability.iloc[0]),
        "matches_saved_prediction": bool(
            np.isclose(p, match.late_probability.iloc[0], rtol=1e-6, atol=1e-8)
        ),
        "model_id": report["model_id"],
        "snapshot_id": report["snapshot_id"],
        "prediction_point": str(frame.approved_at.iloc[0]),
        "approval_time_features": values,
        "scope": "On-demand replay for a historical held-out order, not a live shipment guarantee.",
    }
