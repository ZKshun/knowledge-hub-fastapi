import hashlib
import json
from pathlib import Path

from tests.contract.comparison import assert_equivalent, normalize_response

FIXTURES = Path(__file__).parents[1] / "fixtures/contracts/v1"


def load_case(name: str) -> dict:
    paths = list(FIXTURES.glob(f"*_{name}.json"))
    assert len(paths) == 1, f"Missing or ambiguous captured case: {name}"
    return json.loads(paths[0].read_text(encoding="utf-8"))


def test_evidence_preserves_explicit_same_content_version_increment() -> None:
    created = load_case("create_minimal")
    document_id = created["response"]["body"]["id"]
    assert isinstance(document_id, str)
    for case, version in [
        ("create_minimal", 1),
        ("patch_same_content", 2),
        ("patch_metadata_only", 2),
        ("patch_empty", 2),
        ("patch_summary_only", 2),
        ("patch_content_changed", 3),
    ]:
        snapshot = load_case(case)
        row = next(row for row in snapshot["state"]["mongo"] if row["documentId"] == document_id)
        assert row["version"] == version, case


def test_evidence_preserves_create_and_validation_contracts() -> None:
    assert load_case("create_minimal")["response"]["status"] == 201
    assert load_case("create_empty_title")["response"]["status"] == 201
    assert load_case("create_empty_content")["response"]["status"] == 500
    rejected = load_case("create_unknown_field")["response"]
    assert rejected["status"] == 400
    assert isinstance(rejected["body"]["message"], list)


def test_evidence_records_soft_delete_in_both_databases() -> None:
    record = load_case("delete_primary")
    document_id = record["response"]["body"]["id"]
    assert record["response"]["body"] == {"id": document_id, "deleted": True}
    assert next(row for row in record["state"]["postgres"] if row["id"] == document_id)["deleted"]
    assert next(row for row in record["state"]["mongo"] if row["documentId"] == document_id)[
        "deleted"
    ]
    assert load_case("get_deleted")["response"]["status"] == 404


def test_evidence_records_legacy_compensation_boundaries() -> None:
    normal_failure = load_case("create_postgres_failure")
    assert normal_failure["response"]["status"] == 500
    assert not any(row["content"] == "failed create" for row in normal_failure["state"]["mongo"])
    failed_compensation = load_case("create_compensation_failure")
    assert failed_compensation["response"]["status"] == 500
    assert any(
        row["content"] == "orphan candidate" for row in failed_compensation["state"]["mongo"]
    )


def test_manifest_authenticates_files_and_normalized_records_preserve_raw_evidence() -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sourceCommit"] == "f9dfce20ffe798dc35ede0a74219f06bf3d6980f"
    for entry in manifest["records"]:
        recorded = (FIXTURES / entry["file"]).read_bytes()
        assert hashlib.sha256(recorded).hexdigest() == entry["sha256"], entry["file"]
        record = json.loads(recorded)
        raw = {key: value for key, value in record.items() if key != "normalized"}
        normalized = normalize_response(raw, manifest["normalization"]["bindings"])
        assert_equivalent(normalized, record["normalized"])
    primary = load_case("create_minimal")["normalized"]["response"]["body"]
    assert primary["createdAt"].endswith(";precision=3;timezone=Z")


def test_evidence_contains_an_actual_equal_creation_time_group() -> None:
    record = load_case("list_tied_created_at")
    assert record["response"]["status"] == 200
    items = record["response"]["body"]["items"]
    assert len(items) == 3
    assert items[0]["createdAt"] == items[1]["createdAt"]
    assert items[1]["createdAt"] > items[2]["createdAt"]
    assert {items[0]["title"], items[1]["title"]} == {"Full Contract 知识库", "Archived"}
