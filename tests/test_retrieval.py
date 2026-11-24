"""Focused chunk/provenance tests; real retrieval scoring is a separate measured job."""

import json

from shipsignal.retrieval import chunks, guidance_path


class TestTokenizer:
    def __call__(self, text, **kwargs):
        return {"offset_mapping": [(i, i + 1) for i in range(len(text))]}


def test_chunks_preserve_exact_original_substrings_and_overlap():
    text = "texto com ação, acentuação e caracteres portugueses"
    parts = list(chunks(text, TestTokenizer(), size=12, overlap=3))
    assert parts[0] == text[:12]
    assert parts[1] == text[9:21]
    assert all(part in text for part in parts)
    assert parts[-1].endswith(text[-1])


def test_every_guidance_document_is_explicitly_simulated():
    documents = json.loads(guidance_path().read_text())
    assert len(documents) == 5
    assert len({d["id"] for d in documents}) == 5
    assert all(
        "SIMULATED OPERATIONAL GUIDANCE" in d["text"] and "not an Olist policy" in d["text"]
        for d in documents
    )


def test_guidance_topics_are_explicit_and_multilingual():
    from shipsignal.retrieval import guidance_topics

    assert "sim-damage-v1" in guidance_topics("What should support do when an item is broken?")
    assert "sim-missing-item-v1" in guidance_topics("Como investigar um produto faltando?")
    assert "sim-communication-v1" in guidance_topics("Como responder sem prometer reembolso?")
    assert guidance_topics("chemical composition of neutron stars") == []
