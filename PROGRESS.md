# ShipSignal AI implementation progress

All changes are local to the existing `/workspace/shipsignal-ai` project. **No GitHub commits, pushes, PRs, or deployments are authorized in this implementation turn.** Personal interview coaching stays in chat; public-facing technical documentation belongs in the project only when relevant to setup or review.

## Status

| Milestone | Implementation | Verification | Blockers |
|---|---|---|---|
| 1 — trusted data | Verified; numeric-edit robustness fix added | 20/20 software tests at stage close; real ingestion 56/57 checks with documented exception | No data blocker |
| 2 — analytics | SQL + FastAPI + React dashboard implemented | 22 software tests; frontend build/unit; real SQL/API reconciliation; browser workflow/screenshots passed | No deployment |
| 3 — ML | Both models trained; saved predictions; risk explorer implemented | Chronology tests, prediction replay, measured metrics and browser workflow passed | Weak generalization; experimental only |
| 4 — RAG | Encoder, Chroma index, hybrid guidance retrieval and bounded OpenAI adapter implemented | Real retrieval diagnostics and source/API checks passed; live generation NOT verified | Private OpenAI key unavailable |
| 5 — integration | Integrated React/FastAPI application runs in one-origin production mode | 36 Python tests, 5 browser workflows, build/lint/config checks passed | Live OpenAI call, full app-image execution and external deployment unverified |

## Evidence rules

- Software fixtures do not support business results or model performance claims.
- Historical source coverage and eligible denominators must be explicit.
- No arbitrary text-to-SQL; numerical answers must reference approved executed queries or saved predictions.
- Product/item/payment/review grain must remain explicit.
- Prior owner-reported 56/57 validation result is documented evidence, not a substitute for this environment's run.
- Existing translation lookup exception remains visible; no blanket waiver.

## Commands and changes

Initial audit: read current GitHub tree without mutations; found the existing 32 tracked source/configuration/documentation files. Existing local source folder has no `.git` metadata, so no commit operation is being attempted. Current local files are being compared with remote blob identities before edits. Existing ignored `.env` is preserved and never printed.

Further milestone outcomes, commands, measured results and limitations are appended as work completes.

## Milestone 1 independently verified in this environment

- Downloaded the actual official Kaggle archive (44,717,580 bytes; 9 CSVs) into ignored local storage. No source mirror or generated business data used.
- `ruff check src tests scripts`: passed. Baseline non-database run: 15 passed, 4 deselected.
- `docker compose up -d --wait`: PostgreSQL healthy.
- `shipsignal inspect`: actual source inventory matches the documented owner snapshot.
- `shipsignal validate --source-only`: 34/35 passed. `shipsignal ingest`: loaded raw_dbfbd3a2636389441845. `shipsignal validate`: 56/57 passed; only documented translation coverage failed.
- Fixed a discovered robustness issue: nonnumeric manual edits in PostgreSQL now fail reconciliation without crashing numeric casts.
- Full software suite after the fix: **20 passed**, including five PostgreSQL integration cases.
- Modified `src/shipsignal/database.py`, `tests/test_database.py`; preserved the original ingestion/profile/CLI modules otherwise.
- Raw source and populated `.env` remain ignored. No GitHub mutations.

## Milestone 2 implementation in progress

Added explicit derived order-grain SQL, analytics FastAPI endpoint, React/Plotly dashboard, date/state filters, source definitions, CSV regional export, and empty/error states. Verification pending. The derivative build tolerates only the reviewed category translation finding and requires all database reconciliations to pass.

## Milestone 2 verified

- Created `src/shipsignal/analytics.py`, `settings.py`, `tasks.py`, `api/main.py`, `scripts/run_local.py`, `scripts/verify_analytics.py`, the `frontend/` Vite/React/Plotly application, `tests/test_analytics.py`, frontend unit and Playwright tests.
- Reuses raw snapshots; explicit preaggregation precedes joins. Derived order_fact has a primary key and count reconciliation.
- `python -m shipsignal.tasks analytics`: built **99,441** orders for snapshot dbfbd3a2636389441845929bdfebcf282074943cd8b5db47d9fe5f3de9f87815.
- Full Python software suite with isolated PostgreSQL integration databases: **22 passed**.
- `npm run build`: passed. `npm test`: **1 passed**.
- Live independent raw-order SQL vs API verification: passed, including counts, denominator, grouped conservation and selected state filters. Evidence: `reports/analytics_verification.json`.
- Chromium Playwright analytics workflow: **1 passed**. Verified displayed KPI values against real API results, state filtering, reset, two Plotly charts and mobile heading; no browser errors. Screenshots: `docs/screenshots/analytics-desktop.png`, `analytics-mobile.png`.
- Measured current SQL totals: 96,470 eligible delivered orders, 7,826 late, 8.1123665% late rate; 2,971 orders excluded from delivery metrics. Average delivery duration 12.5582171 days. Timestamp comparison and eligibility are displayed in the app.
- Environment issues resolved: port 8001 is occupied by managed infrastructure, so API uses **8787**; existing system Chromium is used for tests; npm cache placed in ignored workspace. CPU-only XGBoost avoids unnecessary GPU libraries.
- No dashboard/API deployment performed. No commits or pushes.

## Milestone 3 implemented and measured

- Added `src/shipsignal/ml.py`, `/api/models`, `/api/risks`, `frontend/src/Risk.jsx`, `tests/test_ml.py`, `scripts/verify_ml.py`, and `docs/feature_availability.md`.
- Prespecified Logistic Regression and CPU XGBoost; training-only preprocessing, chronological train/calibration/selection/test boundaries; label availability enforced at each cutoff. Review/outcome/promise/payment columns excluded from model features.
- Training data: 54,178 records; calibration: 6,721; validation selection: 7,649; final test: 19,279. Purged immature labels: 3,659 / 2,918 / 1,991 respectively.
- Actual XGBoost test: PR-AUC/AP 0.0607342, ROC-AUC 0.566558, precision 0.0619469, recall 0.00687623, F1 0.0123784, Brier 0.0521318; validation-selected threshold 0.135. Test prevalence 0.0528036.
- Actual Logistic Regression test: PR-AUC/AP 0.0627319, ROC-AUC 0.577262, precision 0.0533659, recall 0.150295, F1 0.0787645, Brier 0.0561526.
- XGBoost remains selected by validation AP, despite Logistic Regression's slightly higher test AP; no tuning to the test results. Both are **experimental**, with weak generalization and temporal calibration drift; not validated for operational decisions.
- Saved both pipeline/calibrator artifacts, actual evaluation JSON and historical test predictions under ignored `artifacts/ml/`. No invented performance values.
- Chronology/features/metric unit tests: **3 passed**. Playwright risk explorer and saved-metric agreement: **1 passed**.
- Risk explorer shows later observed outcomes separately from approval-time predictions and exposes split audit/calibration/model version. Prediction replay verification recorded in `reports/ml_verification.json`.
- Retrieval implementation next; OpenAI selected by owner, key remains unavailable. No GitHub mutations.

## Milestone 4 implemented; real retrieval verified, live generation blocked

- Added `embedding.py`, `retrieval.py`, `assistant.py`, bundled simulated guidance and retrieval cases in `src/shipsignal_data/`, assistant/retrieval/document/capability API routes, React evidence assistant, source viewers, and assistant/retrieval contract tests.
- Quantized ONNX export of the multilingual Sentence Transformers encoder runs locally with normalized masked-mean vectors. Recorded model revision: 2c4055b12046f11709e9df2c122e59ffbdc2f900. No reviews are sent to an embedding API.
- Real corpus: **42,687 nonblank review records**, **42,693 review chunks**, plus **5 simulated guidance documents**, **42,698 total chunks**. Ten SQL candidates containing only Python-defined whitespace were excluded explicitly. Raw structured reviews remain unchanged.
- Resumable indexing paginates Chroma metadata to avoid SQLite variable limits, verifies source hashes, and serializes builds with a file lock. Guidance uses title/action vectors and a labeled English/Portuguese topic fallback, never a fabricated cosine score.
- Actual diagnostic pipeline results: **12/14 supported target-source hits@5 (85.71%)**, MRR@5 **0.702381**, and **2/2 unsupported retrieval abstentions**. Cases are developer-curated paraphrases/translations with incomplete relevance labels, not an independent representative benchmark. Initial guidance failures informed development; the diagnostic score must not be advertised as general RAG accuracy.
- Actual live local API verification covered SQL, risk, Portuguese/English reviews, and simulated guidance. **17/17 retrieved source records** resolved and matched original source text, IDs and hashes; SQL answers agreed exactly with analytics, state filters held, and unsupported live questions abstained. Evidence: `reports/rag_verification.json`.
- OpenAI adapter uses structured source-ID selection with server-owned numerical rendering, not free-form numerical generation. Membership/type/duplicate/count validation rejects invented citations. Missing-key mode is explicitly evidence-only.
- **Live OpenAI generation has NOT been verified**: owner chose OpenAI, but no private API key is configured. Provider calls are mocked only in focused contract tests. No generation-quality score or live-provider claim is fabricated.
- New runtime code is local only; no GitHub writes.

## Milestone 5 local integration verified

- Added same-origin production React serving through FastAPI, `Dockerfile`, `.dockerignore`, optional `compose.app.yaml`, runtime constraints, input validation and safe error responses, full setup/demonstration/deployment docs and actual screenshots.
- Added on-demand `/api/predict/{order_id}` replay for held-out orders only. It reconstructs allowed approval-time features, loads the trusted saved model, checks dataset/model provenance and compares with the saved prediction. Live API check passed for all 19 allowed features; browser test verified recomputation and feature inspection. It is explicitly historical, not live/new-order scoring.
- Tightened DQ-001 acceptance: both counts AND the exact two reviewed categories must match; an adversarial synthetic case with identical counts but different categories is rejected. Raw validation remains strict.
- Final `ruff check src tests scripts`: passed. `ruff format --check`: passed for 33 Python files. `pip check`: no broken requirements.
- `python scripts/test_backend.py --integration`: **36 passed**, no warnings in the final run; temporary integration databases isolated/cleaned.
- `npm --prefix frontend test`: **1 passed**. `npm --prefix frontend run build`: passed. Plotly is lazy-loaded; large chunk size remains a bundle-size tradeoff, not a hidden test failure.
- Final Chromium run against production origin `http://127.0.0.1:8787`: **5 passed**. Covered real analytics/API agreement, state/reset behavior, explicit empty cohorts, SQL/source citations with Portuguese text, unsupported live questions, risk metrics and on-demand model replay. Screenshots regenerated from actual running workflows.
- Strengthened analytics verification by independently recomputing from original CSVs with pandas: all KPI values, **25 monthly groups**, **27 regional groups**, status counts and combined date/state filtering passed.
- `docker compose -f compose.yaml -f compose.app.yaml config --quiet`: passed without printing expanded credentials. `docker build --check`: passed, no warnings. PostgreSQL container was run and healthy. The full app image build/run was NOT performed in this storage-constrained workspace; native same-origin production serving was tested instead.
- Resolved discovered integration issues: reserved SQL alias, accidental managed-port collision, workspace cache/disk limits, Chroma metadata pagination, text-whitespace coverage counts, guidance retrieval mismatch, stale frontend asset handling for missing cosine scores, float32 CSV round-trip tolerance, and configuration lint/fixture warnings. No failing check has been silently counted as passed.
- `docs/evaluation.md` and safe JSON evidence contain actual measured ML/retrieval results, small-diagnostic limitations and the lack of live-LLM evaluation. Existing source setup/data model docs were updated to distinguish historical owner evidence from independent current verification.

## Remaining blockers / limitations

1. **OpenAI live-provider verification:** adapter implemented; private key absent. All demonstrations currently run in explicitly labeled evidence-only mode. No live generation-quality result is claimed. Configure a server-side key privately and run `scripts/verify_rag.py` to verify the actual provider. Never paste a key into chat.
2. **Model usefulness:** held-out discrimination and threshold recall are weak. The application is functional, but the model is experimental and unsuitable for operational decisions without further prospective validation. Do not tune against this already inspected test set.
3. **Deployment:** no deployment target/credentials supplied. Local run, frontend build, native production serving, Dockerfile check and Compose validation are verified; full app-image execution and external deployment are not. Authentication, quotas and persistent artifact/database storage are prerequisites for exposing a live-LLM service publicly.
4. **Evidence limits:** RAG results are developer diagnostics, not independent answer-quality estimates. Source integrity does not establish semantic LLM quality. Static catalog assumptions limit historical point-in-time certainty.
5. **Delivery/approval:** all changes remain in the EXISTING project locally. GitHub has not been changed, committed, pushed or deployed. A source-only bundle and patch are prepared for review; credentials, raw data, generated models/indexes, dependency caches and personal learning materials are excluded. Publishing requires explicit owner approval.


## Authorized GitHub delivery verification

The owner explicitly authorized committing and publishing the existing implementation. Existing public repository: sahithiakunoor/ShipSignal-AI, branch main; baseline 4b668b2ada3fd20f49e24fab74ace8b753b6528c. The working folder has no Git metadata; publication uses the authenticated GitHub connector and preserves the existing parent/history. Earlier no-publication notes describe the previous approval state.

- Re-ran the backend suite: **36 passed** (including isolated PostgreSQL integration).
- Re-ran production-origin Chromium workflows: **5 passed**; frontend unit test: **1 passed**; production frontend build passed.
- Re-ran independent CSV analytics, model replay and RAG/source checks: all passed. Empty-group median verification now explicitly returns undefined instead of emitting a NumPy warning.
- Ruff lint/format and dependency consistency checks passed; Compose validation passed. Existing PostgreSQL container healthy. Existing API server was reused after detecting that port 8787 was already occupied by it.
- README now includes clone/update commands, complete batch/runtime setup and Mac troubleshooting. `.env.example` lists names with blank secret fields. `.gitignore` additionally excludes OS/browser reports, database files and model binary formats. Removed transient browser report output; private data and working notes remain excluded from publication.
- OpenAI is optional: evidence-only mode verified with no key. Live generation remains untested. Full application-image execution and external deployment remain unverified; Mac instructions are provided but tests here ran on Linux.
- Publication is prepared as one source/documentation/screenshots commit, with explicit allowlisting and credential checks. The delivery response reports the actual resulting GitHub commit after remote verification.
