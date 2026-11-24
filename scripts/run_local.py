"""Run a command with the ignored project .env loaded; never display credential values."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
if len(sys.argv) < 2:
    raise SystemExit("Usage: python scripts/run_local.py <command> [arguments...]")
raise SystemExit(subprocess.call(sys.argv[1:], cwd=ROOT, env=os.environ.copy()))
