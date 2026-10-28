"""Run from the repository root: python scripts/capture_legacy_v1.py --help."""

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.legacy_v1.runner import main  # noqa: E402 -- support direct script execution

if __name__ == "__main__":
    main()
