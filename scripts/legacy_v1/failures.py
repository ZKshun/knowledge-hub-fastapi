from scripts.legacy_v1.capture import CaptureSession
from scripts.legacy_v1.database import LegacyDatabase


def capture_failures(capture: CaptureSession, database: LegacyDatabase) -> None:
    capture.record(
        "create_postgres_failure",
        "POST",
        "/documents",
        body={
            "title": "SQL failure",
            "content": "failed create",
            "categoryId": "invalid-bigint",
        },
    )
    database.fail_next_mongo_command("insert")
    capture.record(
        "create_mongo_failure",
        "POST",
        "/documents",
        body={
            "title": "Mongo failure",
            "content": "failed mongo create",
        },
    )
    capture.create("failure_update", {"title": "Update failure", "content": "before failure"})
    database.fail_next_mongo_command("update")
    capture.record(
        "patch_mongo_failure",
        "PATCH",
        "/documents/{failure_update}",
        body={"content": "mongo must not save"},
    )
    capture.record(
        "patch_postgres_failure",
        "PATCH",
        "/documents/{failure_update}",
        body={"content": "mongo changed before SQL failed", "categoryId": "invalid"},
    )
    capture.create("failure_delete", {"title": "Delete failure", "content": "not yet deleted"})
    database.fail_next_mongo_command("update")
    capture.record("delete_mongo_failure", "DELETE", "/documents/{failure_delete}")
    database.fail_next_mongo_command("delete")
    capture.record(
        "create_compensation_failure",
        "POST",
        "/documents",
        body={
            "title": "Compensation failure",
            "content": "orphan candidate",
            "categoryId": "invalid",
        },
    )
    database.disable_failure()
