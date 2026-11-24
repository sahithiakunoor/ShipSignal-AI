# Measured evaluation results

These values were measured in the current implementation environment on the official historical Olist snapshot. They are not tutorial scores or invented targets. Raw files, models, test predictions and the full review corpus stay in ignored local storage.

Snapshot: `dbfbd3a2636389441845929bdfebcf282074943cd8b5db47d9fe5f3de9f87815`. Selected model run: `b4c5c209b975d032`.

## Late-delivery classification

Prediction point: immediately after approval. Conditional target: late delivery among observed delivered orders with valid purchase/approval/outcome ordering. Catalog/seller attributes are assumed static; versioned historical catalog data is unavailable. Exported delivery promise is not an input. See [feature availability](feature_availability.md).

| Model | Precision | Recall | F1 | ROC-AUC | PR-AUC / AP | Brier | Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| logistic_regression | 0.053366 | 0.150295 | 0.078764 | 0.577262 | 0.062732 | 0.056153 | 0.165 |
| xgboost | 0.061947 | 0.006876 | 0.012378 | 0.566558 | 0.060734 | 0.052132 | 0.135 |

Test records: **19,279**. Test late prevalence: **5.280357%**. Prevalence-only baseline AP: **0.052804**; baseline Brier: **0.050065**. PR-AUC here means scikit-learn average precision, not trapezoidal PR area. Lower Brier is better.

**xgboost remains selected by validation AP.** Logistic Regression has slightly higher test AP, but test results are not used to change model selection. Both candidates and their fixed hyperparameters are prespecified in `src/shipsignal/ml.py`. No test tuning was performed.

**Operational conclusion:** the model has weak held-out discrimination and extremely low recall at its selected threshold. Its Brier score also does not improve on the reported prevalence baseline. This is an experimental portfolio model, not validated operational decision support. Temporal prevalence/calibration drift and the consequences of label-maturity purging are visible in the split audit. No causal claims are made.

| Period | Records retained | Unmatured outcomes purged | Approval start | Approval end | Late prevalence |
|---|---:|---:|---|---|---:|
| train | 54,178 | 3,659 | 2016-09-15 12:16:38 | 2018-03-01 10:50:23 | 5.9840% |
| calibration | 6,721 | 2,918 | 2018-03-03 12:55:55 | 2018-04-13 13:35:34 | 10.7573% |
| selection | 7,649 | 1,991 | 2018-04-16 00:13:18 | 2018-05-25 02:54:51 | 1.5819% |
| test | 19,279 | 0 | 2018-05-26 19:38:22 | 2018-08-29 15:10:26 | 5.2804% |

Training preprocessing is fitted only on train. Calibration uses earlier validation; selection and threshold use later validation. The final test cohort follows those periods. A record is purged from a fitting/decision period if its eventual delivery label was not observable by the next cutoff. Purging changes cohort composition and can reduce representation of unresolved late outcomes; these counts must be considered alongside scores. No performance claim applies to canceled, censored, undelivered or future live orders.

Saved artifacts include both pipelines/calibrators, evaluation JSON, the feature contract and test predictions. `scripts/verify_ml.py` replayed predictions, checked training-only median imputation and recomputed the selected model metrics; comparisons allow only the precision required for float32 CSV round trips.

## Retrieval diagnostics

Indexed **42,687 actual review records** as **42,693 chunks**, plus **5 simulated guidance documents**. Total: **42,698 chunks**. Blank source reviews remain in PostgreSQL.

Encoder: `Xenova/paraphrase-multilingual-MiniLM-L12-v2`, immutable revision `2c4055b12046f11709e9df2c122e59ffbdc2f900`. Quantized ONNX CPU inference, masked mean pooling and normalized vectors. Source: exported multilingual Sentence Transformers model. Reviews use cosine search; the tiny guidance collection additionally has a labeled curated-topic fallback.

| Measure | Actual result |
|---|---:|
| Supported target-source hit@5 | 12/14 (85.71%) |
| Mean reciprocal rank@5 | 0.702381 |
| Unsupported retrieval abstentions | 2/2 (100.00%) |
| Retrieved source integrity in API checks | 17/17 |

**Interpretation:** this is a small developer-curated diagnostic set: ten review paraphrase/translation queries, four guidance queries and two unsupported questions. Labels identify specific real source records and are incomplete: an unjudged returned review may also be relevant. Query construction is close to the labeled records. Guidance matching was improved using this development set. These results are not an independent benchmark or a general answer-accuracy estimate. The five-document guidance collection makes hit@5 particularly easy; inspect individual ranks and failures.

The two missing-control review queries did not retrieve the labeled source within the accepted set. Their failure remains in the report; no thresholds were loosened to hide it.

| Case | Language | Kind | Target hit@5 / unsupported abstention |
|---|---|---|---|
| late-pt | pt | review | yes |
| late-en | en | review | yes |
| chair-pt | pt | review | yes |
| chair-en | en | review | yes |
| wrong-pt | pt | review | yes |
| wrong-en | en | review | yes |
| remote-pt | pt | review | no |
| remote-en | en | review | no |
| early-pt | pt | review | yes |
| early-en | en | review | yes |
| guidance-damage-en | en | guidance | yes |
| guidance-missing-pt | pt | guidance | yes |
| guidance-metrics-en | en | guidance | yes |
| guidance-communication-pt | pt | guidance | yes |
| unsupported-en | en | unsupported | yes |
| unsupported-pt | pt | unsupported | yes |

## Assistant verification boundaries

The API checks resolved cited IDs, compared review IDs/order IDs/chunk text against original CSV records, verified hashes, checked simulated labels, matched SQL tool results, enforced customer-state filters and verified unsupported live-question abstention. Source integrity is not semantic answer correctness.

**Live OpenAI generation was not evaluated:** no private API key is configured. The adapter is implemented, while provider behavior is covered only by mocked contract tests. Without a key the app explicitly shows evidence-only mode; it does not claim to generate a live LLM answer. No fabricated LLM accuracy/groundedness score is supplied. To verify a configured provider locally, rerun `scripts/verify_rag.py` after setting a private server-side key; review provider-selected citations and outputs.
