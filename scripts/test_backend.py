"""Run software tests, optionally with isolated PostgreSQL integration databases; redact secrets."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--integration", action="store_true")
args, extra = parser.parse_known_args()
load_dotenv(root / ".env", override=False)
env = os.environ.copy()
if args.integration:
    if not env.get("DATABASE_URL"):
        raise SystemExit("Configure a private local DATABASE_URL first.")
    env["TEST_DATABASE_URL"] = env["DATABASE_URL"]
else:
    extra = ["-m", "not integration", *extra]
result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q", *extra],
    cwd=root,
    env=env,
    check=False,
    capture_output=True,
    text=True,
)
output = result.stdout + result.stderr
for name in ["DATABASE_URL", "TEST_DATABASE_URL", "POSTGRES_PASSWORD", "OPENAI_API_KEY"]:
    value = env.get(name)
    if value:
        output = output.replace(value, "[REDACTED]")
print(output, end="")
raise SystemExit(result.returncode)
