FROM node:22-bookworm-slim AS frontend
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund && npm cache clean --force
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
COPY pyproject.toml README.md requirements-runtime.lock.txt ./
COPY src ./src
RUN python -m pip install -c requirements-runtime.lock.txt . && useradd --create-home --uid 10001 shipsignal && chown -R shipsignal:shipsignal /app
COPY --from=frontend --chown=shipsignal:shipsignal /ui/dist ./frontend/dist
USER shipsignal
EXPOSE 8787
CMD ["uvicorn","shipsignal.api.main:app","--host","0.0.0.0","--port","8787"]
