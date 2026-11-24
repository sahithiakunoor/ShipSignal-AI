"""Multilingual local vector retrieval over actual review records and labeled guidance."""

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

import chromadb
from psycopg import sql

from .analytics import connect, dataset
from .settings import NotReady, Settings


@lru_cache(maxsize=2)
def encoder(repo, cache):
    from .embedding import MultilingualEncoder

    return MultilingualEncoder(repo, cache)


def chunks(text, tokenizer, size=96, overlap=16):
    offsets = tokenizer(
        text, add_special_tokens=False, return_offsets_mapping=True, truncation=False, verbose=False
    )["offset_mapping"]
    for start in range(0, len(offsets), size - overlap):
        segment = offsets[start : start + size]
        if not segment:
            break
        excerpt = text[segment[0][0] : segment[-1][1]]
        if excerpt.strip():
            yield excerpt
        if start + size >= len(offsets):
            break


def guidance_path():
    return Path(__file__).resolve().parents[1] / "shipsignal_data" / "simulated.json"


def _build_index():
    settings = Settings.read()
    embedding = encoder(settings.embedding_model, str(settings.artifacts / "embedding_model"))
    # Bundled guidance has explicit authored provenance, separate from historical source records.
    path = guidance_path()
    guidance = json.loads(path.read_text())
    with connect(settings.database_url) as conn:
        active = dataset(conn)
        query = sql.SQL("""SELECT r.__source_row source_row,r.review_id,r.order_id,r.review_score,
          r.review_comment_title title,r.review_comment_message message,
          f.customer_state,f.purchased_at::date purchase_date
          FROM {} r JOIN analytics.order_fact f USING(order_id)
          WHERE btrim(r.review_comment_title)<>'' OR btrim(r.review_comment_message)<>''
          ORDER BY r.__source_row""").format(sql.Identifier(active["raw_schema"], "reviews"))
        rows = conn.execute(query).fetchall()
    docs = []
    nonblank_records = 0
    for row in rows:
        text = "\n".join(v for v in [row["title"], row["message"]] if v.strip())
        if not text.strip():
            continue
        nonblank_records += 1
        for n, excerpt in enumerate(chunks(text, embedding.tokenizer)):
            identity = f"review:{row['source_row']}:{n}"
            metadata = {
                "kind": "review",
                "source_record": row["source_row"],
                "review_id": row["review_id"],
                "order_id": row["order_id"],
                "review_score": row["review_score"],
                "state": row["customer_state"],
                "purchase_day": row["purchase_date"].toordinal(),
                "source_file": "olist_order_reviews_dataset.csv",
                "chunk": n,
                "snapshot_id": active["snapshot_id"],
                "title": f"Customer review · record {row['source_row']}",
                "content_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
            }
            docs.append({"id": identity, "text": excerpt, "metadata": metadata})
    for guide in guidance:
        embedding_text = guide["title"] + "\n" + guide["action"]
        docs.append(
            {
                "id": guide["id"],
                "text": guide["text"],
                "embedding_text": embedding_text,
                "metadata": {
                    "kind": "guidance",
                    "simulated": True,
                    "title": guide["title"],
                    "action": guide["action"],
                    "embedding_sha256": hashlib.sha256(embedding_text.encode()).hexdigest(),
                    "version": "v1",
                    "source_file": "shipsignal_data/simulated.json",
                    "snapshot_id": active["snapshot_id"],
                    "content_sha256": hashlib.sha256(guide["text"].encode()).hexdigest(),
                },
            }
        )
    guide_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    name = (
        "olist_"
        + active["snapshot_id"][:12]
        + "_"
        + embedding.info["revision"][:8]
        + "_"
        + guide_hash
    )
    client = chromadb.PersistentClient(path=str(settings.artifacts / "chroma"))
    # Explicit rebuild touches this derived collection only; raw source is never changed.
    existing = [c.name for c in client.list_collections()]
    if name in existing:
        collection = client.get_collection(name, embedding_function=None)
        existing_hashes = {}
        existing_embedding_hashes = {}
        for offset in range(0, collection.count(), 500):
            indexed = collection.get(include=["metadatas"], limit=500, offset=offset)
            for id_, meta in zip(indexed["ids"], indexed["metadatas"], strict=True):
                existing_hashes[id_] = meta["content_sha256"]
                existing_embedding_hashes[id_] = meta.get(
                    "embedding_sha256", meta["content_sha256"]
                )
    else:
        collection = client.create_collection(
            name, metadata={"hnsw:space": "cosine"}, embedding_function=None
        )
        existing_hashes = {}
        existing_embedding_hashes = {}
    for doc in docs:
        if (
            doc["id"] in existing_hashes
            and existing_hashes[doc["id"]] != doc["metadata"]["content_sha256"]
        ):
            raise ValueError(
                "Existing indexed chunk differs; version the chunking rule before rebuilding."
            )
    pending = sorted(
        [
            doc
            for doc in docs
            if existing_embedding_hashes.get(doc["id"])
            != doc["metadata"].get("embedding_sha256", doc["metadata"]["content_sha256"])
        ],
        key=lambda doc: len(doc["text"]),
    )
    for start in range(0, len(pending), 256):
        batch = pending[start : start + 256]
        vectors = embedding.encode([d.get("embedding_text", d["text"]) for d in batch])
        collection.upsert(
            ids=[d["id"] for d in batch],
            documents=[d["text"] for d in batch],
            metadatas=[d["metadata"] for d in batch],
            embeddings=vectors.tolist(),
        )
        if start % 5120 == 0:
            print(
                f"Indexed {len(docs) - len(pending) + min(start + len(batch), len(pending))}/{len(docs)} chunks",
                flush=True,
            )
    if collection.count() != len(docs):
        raise ValueError(
            "Unexpected stale chunks in derived index; version the index before rebuilding."
        )
    info = {
        "snapshot_id": active["snapshot_id"],
        "collection": name,
        "model": embedding.info,
        "candidate_review_records": len(rows),
        "review_records_with_text": nonblank_records,
        "whitespace_only_records_skipped": len(rows) - nonblank_records,
        "review_chunks": sum(d["metadata"]["kind"] == "review" for d in docs),
        "simulated_guidance_documents": len(guidance),
        "total_chunks": len(docs),
        "max_cosine_distance": 0.38,
        "guidance_max_cosine_distance": 0.50,
        "guidance_embedding_rule": "title_plus_authored_action_v1",
        "threshold_note": "Review cutoff prespecified; separate guidance cutoff developed on a small diagnostic set. Neither is a confidence probability.",
        "source": "Olist customer review records plus clearly labeled authored simulated guidance.",
    }
    dest = settings.artifacts / "rag"
    dest.mkdir(parents=True, exist_ok=True)
    with (dest / "corpus.jsonl").open("w") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    (dest / "index.pending.json").write_text(json.dumps(info, indent=2))
    (dest / "index.pending.json").replace(dest / "index.json")
    return info


def index(settings=None):
    settings = settings or Settings.read()
    path = settings.artifacts / "rag/index.json"
    if not path.exists():
        raise NotReady("Build the real review index with python -m shipsignal.tasks index first.")
    info = json.loads(path.read_text())
    with connect(settings.database_url) as conn:
        if dataset(conn)["snapshot_id"] != info["snapshot_id"]:
            raise NotReady("Index snapshot mismatch. Rebuild retrieval.")
    embedding = encoder(settings.embedding_model, str(settings.artifacts / "embedding_model"))
    if embedding.info != info["model"]:
        raise NotReady("Embedding model/version mismatch. Rebuild retrieval.")
    collection = chromadb.PersistentClient(path=str(settings.artifacts / "chroma")).get_collection(
        info["collection"], embedding_function=None
    )
    return info, embedding, collection


def guidance_topics(question):
    rules = [
        (r"\b(broken|damaged?|quebrad\w*|danific\w*|avaria\w*)\b", "sim-damage-v1"),
        (r"\b(missing|wrong|falt\w*|errad\w*|incomplet\w*)\b", "sim-missing-item-v1"),
        (
            r"\b(numerical|sql|metrics?|numbers?|cohort\w*|responsib\w*|taxa\w*|m[eé]trica\w*|dados)\b",
            "sim-analysis-v1",
        ),
        (
            r"\b(communicat\w*|reply|respond\w*|comunic\w*|responder|promet\w*|reembolso)\b",
            "sim-communication-v1",
        ),
        (r"\b(delay\w*|late|atras\w*)\b", "sim-delay-v1"),
    ]
    return [id_ for pattern, id_ in rules if re.search(pattern, question, re.IGNORECASE)]


def search(question, kind="review", state=None, start=None, end=None, limit=5):
    info, embedding, collection = index()
    clauses = [{"kind": {"$eq": kind}}]
    if kind == "review":
        if state:
            clauses.append({"state": {"$eq": state}})
        if start:
            clauses.append({"purchase_day": {"$gte": start.toordinal()}})
        if end:
            clauses.append({"purchase_day": {"$lte": end.toordinal()}})
    condition = clauses[0] if len(clauses) == 1 else {"$and": clauses}
    result = collection.query(
        query_embeddings=embedding.encode([question]).tolist(),
        n_results=min(limit, collection.count()),
        where=condition,
        include=["documents", "metadatas", "distances"],
    )
    threshold = (
        info.get("guidance_max_cosine_distance", 0.50)
        if kind == "guidance"
        else info["max_cosine_distance"]
    )
    found = []
    for id_, text, meta, distance in zip(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
        strict=True,
    ):
        if distance <= threshold:
            found.append(
                {
                    "id": id_,
                    "text": text,
                    "metadata": meta,
                    "cosine_distance": float(distance),
                    "retrieval_method": "multilingual_vector",
                }
            )
    # Small authored guidance collection: transparent lexical/topic fallback, not a fake vector score.
    if kind == "guidance" and not found:
        topic_ids = guidance_topics(question)[:limit]
        if topic_ids:
            matched = collection.get(ids=topic_ids, include=["documents", "metadatas"])
            by_id = {
                id_: {
                    "id": id_,
                    "text": text,
                    "metadata": meta,
                    "cosine_distance": None,
                    "retrieval_method": "curated_guidance_topic",
                }
                for id_, text, meta in zip(
                    matched["ids"], matched["documents"], matched["metadatas"], strict=True
                )
            }
            found = [by_id[id_] for id_ in topic_ids if id_ in by_id]
    return {
        "snapshot_id": info["snapshot_id"],
        "documents": found,
        "max_cosine_distance": threshold,
        "query": question,
        "kind": kind,
        "index": info,
    }


def document(id_):
    _, _, collection = index()
    result = collection.get(ids=[id_], include=["documents", "metadatas"])
    if not result["ids"]:
        return None
    return {
        "id": result["ids"][0],
        "text": result["documents"][0],
        "metadata": result["metadatas"][0],
    }


def evaluate():
    # Queries/relevance labels are reviewed against actual original review records, not invented text.
    path = Path(__file__).resolve().parents[1] / "shipsignal_data" / "retrieval_cases.json"
    if not path.exists():
        raise NotReady("Curated real-record retrieval cases are not available.")
    cases = json.loads(path.read_text())
    results = []
    for case in cases:
        retrieved = search(case["question"], kind=case["kind"], limit=5)["documents"]
        relevant = set(case["relevant_ids"])
        ranked = [d["id"] for d in retrieved]
        if relevant:
            hit = bool(set(ranked) & relevant)
            rank = next((i + 1 for i, id_ in enumerate(ranked) if id_ in relevant), None)
            results.append(
                {
                    "id": case["id"],
                    "language": case["language"],
                    "question": case["question"],
                    "hit_at_5": hit,
                    "recall_at_5": len(set(ranked) & relevant) / len(relevant),
                    "reciprocal_rank": 1 / rank if rank else 0,
                    "retrieved_ids": ranked,
                    "relevant_ids": sorted(relevant),
                }
            )
        else:
            results.append(
                {
                    "id": case["id"],
                    "language": case["language"],
                    "question": case["question"],
                    "unsupported_retrieval_abstained": not ranked,
                    "retrieved_ids": ranked,
                }
            )
    supported = [r for r in results if "hit_at_5" in r]
    unsupported = [r for r in results if "unsupported_retrieval_abstained" in r]
    info, _, _ = index()
    report = {
        "snapshot_id": info["snapshot_id"],
        "model": info["model"],
        "cases": results,
        "supported_cases": len(supported),
        "retrieval_pipeline": "multilingual cosine search; explicit topic fallback for simulated guidance only",
        "hit_rate_at_5": sum(r["hit_at_5"] for r in supported) / len(supported),
        "mean_recall_at_5": sum(r["recall_at_5"] for r in supported) / len(supported),
        "mean_reciprocal_rank_at_5": sum(r["reciprocal_rank"] for r in supported) / len(supported),
        "unsupported_cases": len(unsupported),
        "unsupported_retrieval_abstention_rate": sum(
            r["unsupported_retrieval_abstained"] for r in unsupported
        )
        / max(len(unsupported), 1),
        "methodology": "Small developer-curated diagnostic set with actual record IDs. Incomplete relevance judgments; not a representative or independent benchmark.",
        "live_llm_generation_evaluated": False,
    }
    (Settings.read().artifacts / "rag/evaluation.json").write_text(json.dumps(report, indent=2))
    return report


def build_index():
    from filelock import FileLock

    settings = Settings.read()
    settings.artifacts.mkdir(parents=True, exist_ok=True)
    with FileLock(str(settings.artifacts / "rag-build.lock"), timeout=0):
        return _build_index()
