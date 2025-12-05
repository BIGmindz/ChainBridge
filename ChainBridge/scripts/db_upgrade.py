"""Run Alembic upgrade head."""

import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    subprocess.check_call(cmd, cwd=root)


if __name__ == "__main__":
    main()
