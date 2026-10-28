import hashlib
import json
import subprocess
from pathlib import Path

SOURCE_COMMIT = "f9dfce20ffe798dc35ede0a74219f06bf3d6980f"


def verify_export(repository: Path, exported: Path) -> dict[str, str]:
    command = [
        "git",
        "-c",
        f"safe.directory={repository.resolve().as_posix()}",
        "-C",
        str(repository),
    ]
    paths = (
        subprocess.check_output(
            [
                *command,
                "ls-tree",
                "-r",
                "--name-only",
                SOURCE_COMMIT,
                "--",
                "src",
                "init-scripts",
                "package.json",
                "pnpm-lock.yaml",
            ]
        )
        .decode()
        .splitlines()
    )
    if not paths or (exported / ".env").exists():
        raise ValueError("Expected a fixed source export without a real .env file")
    hashes = {}
    for path in paths:
        expected = subprocess.check_output([*command, "show", f"{SOURCE_COMMIT}:{path}"])
        actual = (exported / path).read_bytes()
        if actual != expected:
            raise ValueError(f"Source export differs from fixed commit: {path}")
        hashes[path] = hashlib.sha256(actual).hexdigest()
    return hashes


def runtime_versions(exported: Path) -> dict[str, str]:
    package = json.loads((exported / "package.json").read_text(encoding="utf-8"))
    versions = {"node": subprocess.check_output(["node", "--version"]).decode().strip()}
    for name in package["dependencies"]:
        installed = exported / "node_modules" / name / "package.json"
        versions[name] = json.loads(installed.read_text(encoding="utf-8"))["version"]
    return versions
