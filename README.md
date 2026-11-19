# ShipSignal AI — milestone 1

A historical e-commerce intelligence portfolio project. This delivery implements **trusted-data foundations only**: CSV discovery and preservation, quality profiles, transactional PostgreSQL ingestion, and validation.

**Milestone 1: complete with one documented exception for the owner’s local Olist snapshot.** The owner reported successful PostgreSQL ingestion and **56/57 validation checks passed**; the remaining check concerns 13 products in two categories absent from the supplied translation lookup. The strict validation result remains failed (exit status 1). See [run status and evidence provenance](docs/milestone_1_status.md), [observed dictionary](docs/observed_source_dictionary.md), and [exception DQ-001](docs/data_quality_exceptions.md). These local findings were supplied by the owner; the cloud environment has not independently rerun their dataset. No delivery KPI or model score is claimed.

## Quick start

Python 3.11+ (verified on 3.12), Docker with Compose, and the real Olist CSVs are required for a full data run.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock.txt
python -m pip install --no-deps -e .
python scripts/init_local_env.py
set -a
source .env
set +a
docker compose up -d --wait
```

Download/extract the source CSVs into `data/raw/`; see [setup](docs/setup.md). Then:

```bash
shipsignal inspect --source data/raw --source-url https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
shipsignal validate --source-only
shipsignal ingest
shipsignal validate
```

Review `reports/inspection.json`, `reports/inspection.dictionary.md`, and `reports/validation.json`. A failing quality check is an investigation item, not permission to delete source rows. Source-only validation does not certify database reconciliation. Missing data exits with an actionable error, never generated substitute data.

## Verify software

```bash
ruff check src tests
ruff format --check src tests
pytest -q -m 'not integration'
# Only point this at a disposable local PostgreSQL service. Creates/drops test databases.
export TEST_DATABASE_URL="$DATABASE_URL"
pytest -q
```

Without `TEST_DATABASE_URL`, integration tests explicitly skip. Test fixtures are not Olist records and must never support portfolio business claims.

## Read next

- [Observed source dictionary](docs/observed_source_dictionary.md)
- [Known data-quality exception](docs/data_quality_exceptions.md)

- [Setup and operational commands](docs/setup.md)
- [Data model and grain](docs/data_model.md)
- [Provisional semantic dictionary](docs/data_dictionary.md)
- [Design decisions, alternatives and assumptions](docs/decisions.md)
- [Validation interpretation](docs/validation.md)
- [Milestone status and actual test evidence](docs/milestone_1_status.md)

## Layout

```text
src/shipsignal/   source.py       strict CSV parsing and checksum archive
                 contracts.py    provisional Olist expectations
                 profile.py      actual-file profiles and relationship checks
                 database.py     transactional COPY and reconciliation
                 validation.py   explicit quality gates
                 cli.py          inspect / ingest / validate
 tests/                          synthetic software fixtures and PostgreSQL tests
 docs/                           setup, model, dictionary, assumptions, status
 data/raw/                       user-supplied source files (ignored)
 data/manifests/                  byte-identical content-addressed copies (ignored)
 reports/                        generated evidence (ignored)
 sql/                            SQL examples; executable checks live in database.py
```

There is no dashboard, ML, RAG, FastAPI, or frontend implementation in this milestone. Dependencies for those milestones are intentionally absent. Stop after reviewing trusted-data evidence.
