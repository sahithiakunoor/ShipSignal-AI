"""Quantized CPU inference for an exported multilingual Sentence Transformers model.

The ONNX model is an encoder, not a hosted embedding API. Customer reviews stay local.
Mean pooling uses the attention mask; output vectors are L2-normalized for cosine search.
"""

import os
from pathlib import Path
from threading import Lock

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import json

import numpy as np
import onnxruntime as ort

ort.disable_telemetry_events()
from huggingface_hub import HfApi, hf_hub_download
from transformers import AutoTokenizer


class MultilingualEncoder:
    def __init__(self, repo, cache):
        cache = Path(cache)
        cache.mkdir(parents=True, exist_ok=True)
        manifest = cache / "model_manifest.json"
        if manifest.exists():
            info = json.loads(manifest.read_text())
            if info["repo"] != repo:
                raise ValueError("Embedding cache uses another model; select a new cache.")
            revision = info["revision"]
        else:
            revision = HfApi(token=False).model_info(repo).sha
            info = {
                "repo": repo,
                "revision": revision,
                "file": "onnx/model_quantized.onnx",
                "backend": "onnxruntime-cpu",
                "max_tokens": 128,
                "pooling": "masked_mean_l2",
                "original_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            }
        path = hf_hub_download(
            repo_id=repo,
            filename=info["file"],
            revision=revision,
            cache_dir=cache,
            token=False,
            local_files_only=manifest.exists(),
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            repo,
            revision=revision,
            cache_dir=cache,
            token=False,
            local_files_only=manifest.exists(),
        )
        self.tokenizer.model_max_length = 128
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            path, sess_options=options, providers=["CPUExecutionProvider"]
        )
        self._lock = Lock()
        self.names = {item.name for item in self.session.get_inputs()}
        self.info = info
        manifest.write_text(json.dumps(info, indent=2))

    def _encode(self, texts, batch_size=64):
        outputs = []
        for start in range(0, len(texts), batch_size):
            batch = self.tokenizer(
                texts[start : start + batch_size],
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="np",
            )
            inputs = {k: np.asarray(v, dtype=np.int64) for k, v in batch.items() if k in self.names}
            result = self.session.run(None, inputs)[0]
            if result.ndim == 3:
                mask = np.asarray(batch["attention_mask"], dtype=np.float32)[..., None]
                vectors = (result * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
            else:
                vectors = result
            vectors = vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
            outputs.append(vectors.astype(np.float32))
        return np.concatenate(outputs) if outputs else np.empty((0, 384), dtype=np.float32)

    def encode(self, texts, batch_size=64):
        with self._lock:
            return self._encode(texts, batch_size)
