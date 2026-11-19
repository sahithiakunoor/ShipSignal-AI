"""Strict CSV discovery and byte-preserving, content-addressed snapshots."""

import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path: Path):
    # Empty source fields remain empty strings; UTF-8 Portuguese text is untouched.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader, None)
        if not header or len(set(header)) != len(header):
            raise ValueError(f"{path.name}: missing or duplicate headers")
        if any(not IDENTIFIER.fullmatch(c) or c.startswith("__") for c in header):
            raise ValueError(f"{path.name}: unsupported header; inspect before mapping")
        for row_number, row in enumerate(reader, start=1):
            if len(row) != len(header):
                raise ValueError(f"{path.name}: record {row_number} has wrong field count")
            yield header, row_number, row


def headers(path: Path) -> list[str]:
    # Validate even header-only files via the same parser's header checks.
    list_row = next(rows(path), None)
    if list_row:
        return list_row[0]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle))


def canonical_update(digest, row):
    digest.update(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    digest.update(b"\n")


def preserve(path: Path, archive: Path) -> tuple[Path, str]:
    digest = checksum(path)
    destination = archive / digest / path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        temporary = destination.with_suffix(".copying")
        shutil.copyfile(path, temporary)
        if checksum(temporary) != digest:
            temporary.unlink()
            raise ValueError(f"{path.name}: source changed during snapshot")
        temporary.replace(destination)
    if checksum(destination) != digest:
        raise ValueError(f"{destination}: archive checksum mismatch")
    return destination.resolve(), digest
