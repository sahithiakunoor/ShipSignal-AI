"""Download the official public archive; refuse to overwrite existing source CSVs."""

import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

from shipsignal.contracts import FILES

root = Path(__file__).resolve().parents[1]
source = root / "data/raw"
source.mkdir(parents=True, exist_ok=True)
if list(source.glob("*.csv")):
    raise SystemExit(
        "Existing CSVs left unchanged. Inspect them or use a separate source directory."
    )
destination = root / "work/download/olist.zip"
destination.parent.mkdir(parents=True, exist_ok=True)
url = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
try:
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as output:
        while block := response.read(1024 * 1024):
            output.write(block)
    with zipfile.ZipFile(destination) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if set(names) != set(FILES.values()):
            raise ValueError("Archive inventory changed; review manually.")
        for name in names:
            if Path(name).name != name:
                raise ValueError("Unexpected archive path.")
        for name in names:
            (source / name).write_bytes(archive.read(name))
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".source.json").write_text(
        json.dumps({"url": url, "sha256": digest, "bytes": destination.stat().st_size}, indent=2)
    )
    print(
        f"Downloaded official Olist archive; {len(names)} source CSVs. Run shipsignal inspect next."
    )
except (OSError, zipfile.BadZipFile, ValueError) as exc:
    raise SystemExit(
        f"Official download unavailable or changed ({type(exc).__name__}). Download manually from https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce and extract CSVs into data/raw. No substitute data generated."
    ) from None
