"""Generate local-only credentials without printing them or overwriting an existing file."""

import os
import secrets
from pathlib import Path


def create_env(path: Path) -> None:
    password = secrets.token_hex(32)
    content = (
        "POSTGRES_USER=shipsignal\n"
        f"POSTGRES_PASSWORD={password}\n"
        "POSTGRES_DB=shipsignal\n"
        f"DATABASE_URL=postgresql://shipsignal:{password}@localhost:5433/shipsignal\n"
    )
    # Exclusive create prevents accidental credential replacement; restrictive mode on Unix.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / ".env"
    try:
        create_env(target)
    except FileExistsError:
        raise SystemExit("Existing .env left unchanged. See docs/setup.md for rotation.") from None
    print("Created private local .env. Values were not printed; do not commit this file.")
