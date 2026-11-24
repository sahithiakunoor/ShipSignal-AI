"""Live local API/evidence checks, separate from unavailable live OpenAI evaluation."""

import csv
import hashlib
import json
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8787"
client = httpx.Client(base_url=BASE, timeout=90, trust_env=False)
capabilities = client.get("/api/capabilities").json()
questions = [
    ("What is the late delivery rate?", "analytics"),
    ("Which orders have the highest predicted delivery risk?", "risk"),
    ("A entrega está atrasada e sem previsão de quando vai chegar", "reviews"),
    ("The chair arrived on time but was broken underneath.", "reviews"),
    ("What should support do when an item is broken?", "guidance"),
]
all_docs = {}
responses = []
for question, mode in questions:
    r = client.post("/api/assistant", json={"question": question, "mode": mode})
    r.raise_for_status()
    body = r.json()
    assert not body["abstained"], (question, body["answer"])
    if not capabilities["live_openai_configured"]:
        assert body["generation_status"] == "not_configured"
    for doc in body["documents"]:
        all_docs[doc["id"]] = doc
    returned = {d["id"] for d in body["documents"]} | {
        "sql:delivery_overview_v1",
        "ml:saved_test_predictions_v1",
    }
    assert all(c["id"] in returned for c in body["citations"])
    responses.append(
        {
            "mode": mode,
            "generation_status": body["generation_status"],
            "citations": len(body["citations"]),
        }
    )
# Unsupported question is an intentional abstention, not an empty successful answer.
r = client.post("/api/assistant", json={"question": "Where is my package right now?"})
r.raise_for_status()
assert r.json()["abstained"] and not r.json()["citations"]
# Numeric result is byte-for-byte the verified tool result, not LLM prose arithmetic.
analytics = client.get("/api/analytics").json()
answer = client.post(
    "/api/assistant", json={"question": "What is the late delivery rate?", "mode": "analytics"}
).json()
assert answer["facts"]["kpis"] == analytics["kpis"]
scoped = client.get("/api/retrieval", params={"question": "entrega atrasada", "state": "RJ"}).json()
assert all(d["metadata"]["state"] == "RJ" for d in scoped["documents"])
# Resolve cited IDs and verify against actual original records and bundled simulated guidance.
needed = {
    d["metadata"]["source_record"] for d in all_docs.values() if d["metadata"]["kind"] == "review"
}
original = {}
with Path("data/raw/olist_order_reviews_dataset.csv").open(
    encoding="utf-8-sig", newline=""
) as handle:
    for n, row in enumerate(csv.DictReader(handle), 1):
        if n in needed:
            original[n] = row
simulated = {d["id"]: d for d in json.loads(Path("src/shipsignal_data/simulated.json").read_text())}
for id_, doc in all_docs.items():
    response = client.get("/api/documents/" + id_)
    response.raise_for_status()
    resolved = response.json()
    assert resolved["text"] == doc["text"]
    assert hashlib.sha256(doc["text"].encode()).hexdigest() == doc["metadata"]["content_sha256"]
    if doc["metadata"]["kind"] == "review":
        row = original[doc["metadata"]["source_record"]]
        text = "\n".join(
            v for v in [row["review_comment_title"], row["review_comment_message"]] if v.strip()
        )
        assert doc["text"] in text
        assert row["order_id"] == doc["metadata"]["order_id"]
        assert row["review_id"] == doc["metadata"]["review_id"]
    else:
        assert doc["text"] == simulated[id_]["text"] and doc["metadata"]["simulated"] is True
result = {
    "passed": True,
    "assistant_workflows": responses,
    "verified_source_records": len(all_docs),
    "citation_source_integrity": 1.0,
    "sql_answer_agreement": True,
    "review_state_filter": True,
    "unsupported_scope_abstention": True,
    "live_llm_generation_evaluated": capabilities["live_openai_configured"],
    "note": "Source-integrity verification is not a semantic LLM answer-quality score.",
}
Path("reports/rag_verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
