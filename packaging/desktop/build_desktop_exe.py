"""Build the Sera compatibility launcher as a PyInstaller onedir distribution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = Path(__file__).with_name("desktop.spec")


def main() -> int:
    command = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(SPEC_PATH)]
    return subprocess.call(command, cwd=PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
