"""Runtime settings; secret values are never serialized in responses."""

import os
from dataclasses import dataclass
from pathlib import Path


class NotReady(RuntimeError):
    """A required dataset, model, index or provider is unavailable."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    artifacts: Path
    embedding_model: str
    llm_model: str
    llm_key: str

    @classmethod
    def read(cls):
        return cls(
            os.environ.get("DATABASE_URL", ""),
            Path(os.environ.get("ARTIFACTS_DIR", "artifacts")),
            os.environ.get("EMBEDDING_MODEL", "Xenova/paraphrase-multilingual-MiniLM-L12-v2"),
            os.environ.get("LLM_MODEL", "gpt-4.1-mini"),
            os.environ.get("OPENAI_API_KEY", ""),
        )
