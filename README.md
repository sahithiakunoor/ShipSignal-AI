# ShipSignal AI — milestone 1

A historical e-commerce intelligence portfolio project. This delivery implements **trusted-data foundations only**: CSV discovery and preservation, quality profiles, transactional PostgreSQL ingestion, and validation.

**Status: Olist data was not available locally. No actual Olist counts, schema findings, quality results, business metrics, or model scores are asserted.** The pipeline has been tested with explicitly synthetic software fixtures. Download the real files using [setup instructions](docs/setup.md), then run inspection before reviewing or accepting provisional contracts.

## Quick start

Python 3.11+ (verified on 3.12), Docker with Compose, and the real Olist CSVs are required for a full data run.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock.txt
python -m pip install --no-deps -e .
cp .env.example .env
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
