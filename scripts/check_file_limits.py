import argparse
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

MAX_LINES = 300
_SOURCE_ROOTS = ("src", "scripts")


@dataclass(frozen=True)
class FileSize:
    path: Path
    lines: int


def _reject_link(path: Path) -> None:
    if path.is_symlink() or path.is_junction():
        raise ValueError(f"Linked paths are not allowed in production roots: {path}")


def _raise_walk_error(error: OSError) -> None:
    raise error


def inspect_files(root: Path) -> list[FileSize]:
    sizes = []
    for folder in _SOURCE_ROOTS:
        source_root = root / folder
        _reject_link(source_root)
        if not source_root.is_dir():
            raise ValueError(f"Missing production directory: {source_root}")
        for current, directories, filenames in os.walk(source_root, onerror=_raise_walk_error):
            for directory in directories:
                _reject_link(Path(current) / directory)
            for filename in filenames:
                path = Path(current) / filename
                if path.suffix.lower() == ".py":
                    _reject_link(path)
                    with path.open(encoding="utf-8", newline=None) as source:
                        lines = sum(1 for _ in source)
                    sizes.append(FileSize(path=path.relative_to(root), lines=lines))
    return sorted(sizes, key=lambda item: item.path.as_posix())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enforce physical Python file limits")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        sizes = inspect_files(args.root.absolute())
    except (OSError, UnicodeError, ValueError) as error:
        print(f"File limit check failed: {error}", file=sys.stderr)
        return 2
    violations = [item for item in sizes if item.lines > MAX_LINES]
    for item in violations:
        print(f"{item.path.as_posix()}: {item.lines} lines (limit {MAX_LINES})")
    maximum = max((item.lines for item in sizes), default=0)
    print(f"Checked {len(sizes)} Python files; maximum {maximum}/{MAX_LINES} physical lines.")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
