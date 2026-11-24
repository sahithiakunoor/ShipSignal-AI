"""Explicit reproducible jobs extending the existing shipsignal ingestion CLI."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["analytics", "train", "index", "evaluate-rag"])
    parser.add_argument("--manifest", type=Path, default=Path("reports/inspection.json"))
    args = parser.parse_args()
    if args.task == "analytics":
        from .analytics import build

        result = build(os.environ["DATABASE_URL"], json.loads(args.manifest.read_text()))
    elif args.task == "train":
        from .ml import train

        result = train()
    elif args.task == "index":
        from .retrieval import build_index

        result = build_index()
    else:
        from .retrieval import evaluate

        result = evaluate()
    print(json.dumps(result, default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
