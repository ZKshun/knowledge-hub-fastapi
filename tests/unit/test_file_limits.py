import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[2] / "scripts" / "check_file_limits.py"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "scripts").mkdir()
    return tmp_path


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def test_300_lines_pass_and_301_fail_in_production_and_scripts(project: Path) -> None:
    source = project / "src" / "module.py"
    source.write_text("\n" * 300, encoding="utf-8")
    assert run_checker(project).returncode == 0
    source.write_text("\n" * 301, encoding="utf-8")
    (project / "scripts" / "operation.py").write_text("\n" * 301, encoding="utf-8")
    result = run_checker(project)
    assert result.returncode == 1
    assert "src/module.py: 301" in result.stdout
    assert "scripts/operation.py: 301" in result.stdout


def test_last_line_without_newline_counts(project: Path) -> None:
    (project / "src" / "module.py").write_text("\n" * 300 + "pass", encoding="utf-8")
    result = run_checker(project)
    assert result.returncode == 1
    assert "301" in result.stdout


@pytest.mark.parametrize("ending", [b"\r\n", b"\r", b"\n"])
def test_physical_newlines_are_counted_once(project: Path, ending: bytes) -> None:
    (project / "src" / "module.PY").write_bytes(b"# comment" + ending * 300)
    assert run_checker(project).returncode == 0


def test_unicode_line_separator_inside_string_is_not_a_physical_newline(project: Path) -> None:
    content = ('text = "中\u2028文"\n' * 300).encode()
    (project / "src" / "module.py").write_bytes(content)
    assert run_checker(project).returncode == 0


def test_only_production_roots_are_scanned_without_generated_directory_loophole(
    project: Path,
) -> None:
    for directory in ("migrations/versions", "tests", "src/generated"):
        folder = project / directory
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "large.py").write_text("\n" * 301, encoding="utf-8")
    result = run_checker(project)
    assert result.returncode == 1
    assert "src/generated/large.py" in result.stdout
    assert "migrations/versions" not in result.stdout
    assert "tests/large.py" not in result.stdout


def test_missing_production_roots_are_an_error(tmp_path: Path) -> None:
    result = run_checker(tmp_path)
    assert result.returncode == 2
    assert "src" in result.stderr


def test_unreadable_encoding_cannot_silently_pass(project: Path) -> None:
    (project / "src" / "bad.py").write_bytes(b"\xff")
    result = run_checker(project)
    assert result.returncode == 2
    assert "File limit check failed" in result.stderr


def test_linked_source_cannot_bypass_the_check(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.check_file_limits import inspect_files

    (project / "src" / "linked.py").write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(Path, "is_symlink", lambda path: path.name == "linked.py")
    with pytest.raises(ValueError, match="Linked paths"):
        inspect_files(project)
