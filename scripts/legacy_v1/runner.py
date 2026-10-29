import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scripts.legacy_v1.capture import CaptureSession
from scripts.legacy_v1.database import LegacyDatabase
from scripts.legacy_v1.failures import capture_failures
from scripts.legacy_v1.guards import TEST_DATABASE, validate_http_target
from scripts.legacy_v1.lifecycle import capture_lifecycle
from scripts.legacy_v1.source import SOURCE_COMMIT, runtime_versions, verify_export
from scripts.legacy_v1.validation import capture_validation

ROOT = Path(__file__).resolve().parents[2]
POSTGRES_DSN = "postgresql://kh_test:local-contract-only@127.0.0.1:55432/knowledge_hub_fastapi_test"
MONGO_URI = "mongodb://127.0.0.1:57017/knowledge_hub_fastapi_test"


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture the isolated, fixed NestJS v1 contract")
    parser.add_argument("--base-url", default="http://127.0.0.1:3101")
    parser.add_argument("--output", type=Path, default=ROOT / "tests/fixtures/contracts/v1")
    parser.add_argument("--source-repo", type=Path, default=ROOT.parent / "knowledge-hub-backend")
    parser.add_argument("--source-export", type=Path, default=ROOT / ".local/legacy-v1")
    parser.add_argument("--postgres-dsn", default=POSTGRES_DSN)
    parser.add_argument("--mongo-uri", default=MONGO_URI)
    args = parser.parse_args()
    validate_http_target(args.base_url)
    if any(args.output.glob("*.json")):
        parser.error("Output already contains evidence; choose a fresh directory")
    source_hashes = verify_export(args.source_repo, args.source_export)
    database = LegacyDatabase(args.postgres_dsn, args.mongo_uri)
    try:
        database.reset()
        with httpx.Client(base_url=args.base_url, timeout=15, trust_env=False) as http:
            health = http.get("/")
            if health.status_code != 200 or health.text != "Hello World!":
                raise ValueError("Legacy baseline health check failed")
            capture = CaptureSession(http, database, args.output)
            capture_lifecycle(capture, database)
            capture_validation(capture)
            capture_failures(capture, database)
            database.seed_creation_tie([capture.documents["full"], capture.documents["archived"]])
            capture.record("list_tied_created_at", "GET", "/documents?page=1&pageSize=3")
            write_manifest(capture, args.source_export, source_hashes)
    finally:
        database.close()
    print(f"Captured {len(capture.records)} real HTTP/database cases in {args.output}")


def write_manifest(capture: CaptureSession, exported: Path, source_hashes: dict[str, str]) -> None:
    manifest = {
        "sourceCommit": SOURCE_COMMIT,
        "capturedAt": datetime.now(UTC).isoformat(),
        "evidenceType": "real-nestjs-http-and-postgres-mongodb-snapshots",
        "database": TEST_DATABASE,
        "httpPort": 3101,
        "sourceFilesSha256": source_hashes,
        "compiledMainSha256": hashlib.sha256((exported / "dist/main.js").read_bytes()).hexdigest(),
        "runtimeVersions": runtime_versions(exported),
        "records": [
            {
                "file": name,
                "sha256": hashlib.sha256((capture.output / name).read_bytes()).hexdigest(),
            }
            for name in capture.records
        ],
        "normalization": {
            "strategy": "explicit observed scalar bindings; raw records retained",
            "bindings": capture.bindings,
            "preserved": [
                "scalar types",
                "field presence",
                "list order",
                "cross-record identity",
                "timestamp precision and timezone notation",
            ],
        },
        "unorderedWithinTieCases": ["list_tied_created_at"],
        "tieFixtureSetup": {
            "documents": ["full", "archived"],
            "createdAt": "2099-01-01T00:00:00",
            "assertion": "Preserve group order and every field; allow reorder only within equal times",
        },
        "reliabilityCases": "Legacy failure states are evidence of old defects, not required new defects",
        "failureInjectionReference": "https://github.com/mongodb/mongo/wiki/The-failCommand-fail-point",
    }
    with (capture.output / "manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=True, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
