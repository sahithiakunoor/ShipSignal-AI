# Local production serving and deployment preparation

## Verified execution path

Build the frontend with `npm --prefix frontend ci` then `npm --prefix frontend run build`. Run FastAPI from project root with private .env loaded:

```bash
python scripts/run_local.py uvicorn shipsignal.api.main:app --host 127.0.0.1 --port 8787
```

Open http://localhost:8787. This is one origin serving static React assets and /api, independent of the Vite development server. /docs exposes the typed API contract; /api/health is process readiness, not proof that data/artifacts are initialized.

## Optional Compose application service

The original PostgreSQL service remains in compose.yaml. compose.app.yaml adds the application image and mounts generated artifacts; it does not download data or train models at startup.

```bash
# Run from project root after completing local ingestion, analytics, training and indexing.
export LOCAL_UID=$(id -u)
export LOCAL_GID=$(id -g)
docker compose -f compose.yaml -f compose.app.yaml up --build -d --wait
```

The generated password uses URL-safe hexadecimal characters. If you manually choose a password with URI-reserved characters, URL-encode it in a custom DATABASE_URL instead of interpolating it unencoded into compose.app.yaml. Never print or share `docker compose config` with populated environment values; it can render credentials. Host/container user IDs must permit reading/writing mounted artifacts; the user-ID override above avoids assuming that the Mac owner is UID 1000. Back up data/artifacts before managing volumes. Do not delete pgdata to reset or rotate a password.

The Dockerfile is a multi-stage Node/Python build, excludes populated environment files, raw data, model artifacts, private work and test caches, and runs as a nonroot application user. The image does not contain a populated .env or model/index data. Check PROGRESS.md for whether this environment completed an image build; do not infer that a supplied Dockerfile has been exercised.

## External deployment prerequisites

A container host such as a private VM or a service with a persistent disk can run the application. Configure managed PostgreSQL and a persistent artifact directory; run the explicit batch initialization jobs before serving users. Chroma and model/encoder caches must survive restarts. A stateless serverless filesystem is insufficient without redesigning artifact storage.

Store DATABASE_URL and optional OPENAI_API_KEY in the platform's secret manager. Configure LLM_MODEL and ARTIFACTS_DIR as server-side settings. Never put an API key into VITE_* variables or frontend files. Database credentials used to build/load data should be separated from a restricted read-only serving role before an external production deployment.

The portfolio application currently has no multi-user authentication or request quotas. Keep it on a private network or behind an authenticated reverse proxy. Add TLS, authentication, provider spend limits and appropriate request limits before exposing live LLM calls publicly. No external deployment was attempted because no deployment target or credentials were supplied.

## Refresh and recovery

Keep original input snapshots; do not edit raw source to satisfy a test. Reinspect changed bytes, ingest a new raw schema, validate, and explicitly rebuild derivatives. Retrain and reindex for a new active dataset; stale model/index snapshots are rejected. Full validation still returns exit status 1 for the documented translation exception. Other failures must be investigated rather than automatically accepted.

Interrupted review indexing can resume verified chunks in the same derived collection. Only the completed index manifest activates retrieval. Schema/index version changes must be deliberate. No recurring automation or auto-deployment is configured.
