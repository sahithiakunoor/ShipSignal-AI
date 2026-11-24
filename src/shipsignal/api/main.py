"""Read-only analytics API. Later stages register model and assistant endpoints here."""

import logging
from datetime import date

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from shipsignal.analytics import overview
from shipsignal.settings import NotReady, Settings

log = logging.getLogger(__name__)
app = FastAPI(
    title="ShipSignal AI",
    version="0.2.0",
    description="Historical Olist intelligence. No live logistics data.",
)


@app.exception_handler(NotReady)
async def not_ready(request: Request, exc: NotReady):
    return JSONResponse(status_code=503, content={"detail": str(exc), "code": "not_ready"})


@app.exception_handler(psycopg.Error)
async def database_error(request: Request, exc: psycopg.Error):
    log.error("Database request failed (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable or analytics not built. Check setup.",
            "code": "database_unavailable",
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "historical": True}


@app.get("/api/analytics")
def analytics(
    start: date | None = None,
    end: date | None = None,
    state: str | None = Query(default=None, pattern="^[A-Z]{2}$"),
):
    if start and end and start > end:
        raise HTTPException(422, "Start date must not follow end date.")
    return overview(Settings.read().database_url, start, end, state)


@app.get("/api/models")
def models():
    from shipsignal.ml import load_report

    return load_report()


@app.get("/api/risks")
def delivery_risks(
    state: str | None = Query(default=None, pattern="^[A-Z]{2}$"),
    minimum: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    start: date | None = None,
    end: date | None = None,
):
    from shipsignal.ml import risks

    if start and end and start > end:
        raise HTTPException(422, "Start date must not follow end date.")
    return risks(state, minimum, limit, offset, start, end)


from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    mode: Literal["auto", "analytics", "risk", "reviews", "guidance"] = "auto"
    state: str | None = Field(default=None, pattern="^[A-Z]{2}$")
    start: date | None = None
    end: date | None = None
    order_id: str | None = Field(default=None, pattern="^[a-f0-9]{32}$")

    @model_validator(mode="after")
    def ordered_dates(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("Start must not follow end.")
        if not self.question.strip():
            raise ValueError("Question must contain text.")
        return self


@app.post("/api/assistant")
def assistant(body: AssistantRequest):
    from shipsignal.assistant import answer

    return answer(**body.model_dump())


@app.get("/api/retrieval")
def retrieval(
    question: str = Query(min_length=3, max_length=1200),
    kind: Literal["review", "guidance"] = "review",
    state: str | None = Query(default=None, pattern="^[A-Z]{2}$"),
    start: date | None = None,
    end: date | None = None,
):
    from shipsignal.retrieval import search

    if start and end and start > end:
        raise HTTPException(422, "Start must not follow end.")
    return search(question, kind, state, start, end)


@app.get("/api/documents/{document_id}")
def source_document(document_id: str):
    from shipsignal.retrieval import document

    if not __import__("re").fullmatch(r"[A-Za-z0-9:_-]{1,100}", document_id):
        raise HTTPException(422, "Invalid source ID.")
    result = document(document_id)
    if not result:
        raise HTTPException(404, "Source record not found.")
    return result


@app.get("/api/capabilities")
def capabilities():
    s = Settings.read()
    return {
        "historical": True,
        "live_openai_configured": bool(s.llm_key),
        "model_artifacts_present": (s.artifacts / "ml/evaluation.json").exists(),
        "retrieval_artifacts_present": (s.artifacts / "rag/index.json").exists(),
        "model_status": "experimental",
        "llm_model": s.llm_model,
    }


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    log.error("Request dependency failed (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected service error occurred. Check local setup and dependency availability. No credentials were included in this response.",
            "code": "service_error",
        },
    )


@app.post("/api/predict/{order_id}")
def predict_order(order_id: str):
    import re

    from shipsignal.ml import recompute

    if not re.fullmatch(r"[a-f0-9]{32}", order_id):
        raise HTTPException(422, "Provide an Olist order ID from the held-out explorer.")
    result = recompute(order_id)
    if result is None:
        raise HTTPException(404, "Order is not in the evaluated held-out cohort.")
    return result


# The production build serves one origin; development uses Vite's /api proxy.
import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles

static_dir = Path(os.environ.get("FRONTEND_DIST", "frontend/dist"))
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="dashboard")
