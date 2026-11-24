# Approval-time feature contract

Prediction point: the historical `order_approved_at` timestamp. The model target is conditional on delivered orders whose actual/promise timestamps are observed and whose approval follows purchase and precedes actual delivery. Non-delivery/cancellation is not this target.

## Allowed model inputs

- Purchase/approval calendar month, hour and weekday; elapsed purchase-to-approval hours.
- Customer state, seller-state set and dominant source product category.
- Item count, distinct seller/category counts, item/freight totals.
- Aggregate product weight and dimensions; catalog missingness is imputed using training data.

Availability assumption: ordered items, their quoted prices/freight and customer destination are known after approval; catalog/seller attributes are treated as static in this export. Olist does not supply versioned catalog history, so perfect point-in-time reconstruction of catalog changes cannot be certified. Seller IDs and person IDs are not model features; there are no outcome-derived seller aggregates.

## Excluded from model inputs

Actual delivery/carrier dates, reviews/scores, final order status, shipping-limit date, exported delivery-promise interval, payment aggregates, order/customer identifiers, and future outcome summaries. Actual delivery, final status and estimated date are used only for cohort/label construction and label-maturity checks, never as feature columns. The promise interval is excluded because the export cannot prove the promise version known at approval. Payment sequences lack per-event timestamps and are therefore excluded.

## Temporal evaluation

Order approval timestamps define chronological boundaries. The early 60% is the training period; the following 20% is validation, subdivided into calibration and selection/threshold periods; the last 20% is a final test period. Records whose delivery outcome was not observable by the next fitting/decision cutoff are purged from the corresponding training/calibration/selection period. All data transformations are fit on training only. Sigmoid probability calibration uses only the earlier validation subperiod. Model choice and F1 threshold use only later validation. Final test metrics are calculated after those choices are fixed, for both prespecified candidates. Test scores are not used for tuning.

Preprocessing: median-imputed and standardized numeric features, constant-imputed categorical features with bounded one-hot categories and unseen-category handling. Logistic Regression is a baseline; fixed-parameter CPU XGBoost is the challenger. No grid search is performed. Report precision, recall, F1, ROC-AUC, average precision (reported as PR-AUC/AP), Brier score, reliability bins and precision/recall in the top 10% review capacity. A prevalence-only baseline supplies context.

The historical test cohort includes only observed delivery outcomes. Its scores do not establish performance on live, censored, canceled or unavailable orders. Product patterns, calibration and operations can drift over time. Feature effects are associations, not causal explanations.
