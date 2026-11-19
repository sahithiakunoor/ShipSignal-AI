# Setup and first real-data run

## Obtain the actual source

Source: [Olist Brazilian E-Commerce public dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

1. Open the source page, review the dataset description and license, and download the dataset archive. Kaggle may require an account or agreement to its terms.
2. Keep the original ZIP outside version control. Record the selected release/version and download date in your own source notes; the pipeline records file checksums, source URL and inspection/load timestamps.
3. Extract the CSV files directly into `data/raw/`, without editing or re-saving them in a spreadsheet. Do not place unrelated CSVs there. The inspector lists unknown filenames as an error so schema changes require deliberate mapping.
4. Run `shipsignal inspect` before accepting any column or key assumptions. Do not copy example counts from online tutorials.

Optional Kaggle CLI (requires separately installing `kaggle` and configuring your own credentials as described by Kaggle; never put credentials in this repository):

```bash
kaggle datasets download -d olistbr/brazilian-ecommerce -p work/download
python -m zipfile -e work/download/brazilian-ecommerce.zip data/raw
```

The commands do not substitute a mirror, generated dataset, or downloaded sample. Extraction paths can vary; check that the actual CSVs are directly under `data/raw/`.

## Environment

Run commands from the project root, in bash:

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
docker compose ps
```

`requirements-dev.lock.txt` pins the versions used for verification on Python 3.12; `pyproject.toml` describes compatible ranges. The lock is a version snapshot, not a hash-verified cross-platform lock. PostgreSQL uses a versioned image rather than `latest`. The port is bound to loopback only. Change the port and DSN together if 5433 is occupied. The setup script generates a unique local password into an ignored, private `.env` file. No password is supplied by the repository.

An existing PostgreSQL 16 instance also works: set `DATABASE_URL` directly to a database where your role can create schemas and tables. A `.env` file is **not** automatically read by Python; export it as above. Do not commit it.

## Existing database passwords

Changing `.env` or `POSTGRES_PASSWORD` does not change an already initialized PostgreSQL volume. If you previously used a committed password, treat it as exposed. For the local Compose database, change it interactively without putting it in shell history:

```bash
docker compose exec postgres psql -U shipsignal -d shipsignal
```

At the psql prompt, run `\password shipsignal` and follow the hidden password prompts, then `\q`. Update your ignored local `.env` to match (URL-encode the password in `DATABASE_URL`). Rotate it anywhere else you reused it. Do not delete the data volume as a password-rotation method.

The initialization helper refuses to overwrite an existing `.env`. It is for a fresh local setup, not database password rotation. Do not paste generated passwords into chat or commit them.

## Inspect, review, ingest, validate

```bash
shipsignal inspect --source data/raw --archive data/manifests --output reports/inspection.json --source-url https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
shipsignal validate --source-only --output reports/source-validation.json
shipsignal ingest --manifest reports/inspection.json
shipsignal validate --manifest reports/inspection.json --output reports/validation.json
```

Before ingestion, review discovered columns, missing tables, candidate keys, duplicates, null/blank rates, date ranges, malformed timestamps, money fields, and orphan relationships. Contracts are provisional until this review. Inspecting a partial release is allowed; validation then fails coverage rather than pretending the release is complete. Ingesting imperfect raw data is intentional and may follow a failed source-quality check: it preserves evidence without declaring it trusted.

Exit codes: `0` completed/passed, `1` validation findings, `2` setup/parse/connection error. An operational exception does not generate a fresh validation result: check the exit code and report timestamp rather than reading a stale report.

Inspection archives each file under `data/manifests/<full-file-sha256>/<original-name>`. Manifest paths are absolute for the current machine; after moving the project, run inspection again. A snapshot ID is a hash of logical table names and file checksums. Changed bytes produce a new snapshot and raw schema. Repeating an unchanged ingestion reports `already_loaded`; always run validation afterward to detect manual database changes. The loader never truncates or repairs a previous snapshot.

Rows use CSV **record** numbers, not physical line numbers: review comments can contain newlines. The original bytes are retained in the archive; the database stores parsed field strings, not original CSV quoting or BOM bytes. No automatic deduplication, imputation, trimming, timezone conversion, or category normalization occurs.

## Test and stop

```bash
ruff check src tests
ruff format --check src tests
pytest -q -m 'not integration'
export TEST_DATABASE_URL="$DATABASE_URL"
pytest -q
```

Integration tests create isolated, randomly named databases with `shipsignal_test_` prefixes and drop them afterward, using the configured role. They require `CREATEDB`; use a dedicated local service. They do not need Olist data. Automated data validation on real Olist is the separate `shipsignal validate` command.

```bash
docker compose stop
# Resume later without deleting stored data:
docker compose up -d --wait
```

Do not delete the database volume or checksum archive as part of a rerun. Local archives are not backups; retain the original downloaded ZIP separately.
