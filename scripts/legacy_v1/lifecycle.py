from scripts.legacy_v1.capture import CaptureSession
from scripts.legacy_v1.database import LegacyDatabase


def capture_lifecycle(capture: CaptureSession, database: LegacyDatabase) -> None:
    content = "# 知识库\nhello world 🧠"
    capture.create("minimal", {"title": "Contract Alpha", "content": content})
    capture.record("list_default", "GET", "/documents")
    capture.record("get_primary", "GET", "/documents/{minimal}")
    patches: list[tuple[str, dict[str, object]]] = [
        ("patch_same_content", {"content": content}),
        ("patch_metadata_only", {"title": "Contract Alpha revised"}),
        ("patch_empty", {}),
        ("patch_summary_only", {"summary": "explicit summary"}),
        ("patch_content_changed", {"content": "新正文 updated content"}),
        ("patch_publish", {"status": 1}),
        ("patch_published_again", {"status": 1}),
        ("patch_archive", {"status": 2}),
        ("patch_draft", {"status": 0}),
    ]
    for name, body in patches:
        capture.record(name, "PATCH", "/documents/{minimal}", body=body)
    capture.record("delete_primary", "DELETE", "/documents/{minimal}")
    capture.record("get_deleted", "GET", "/documents/{minimal}")
    capture.record("delete_again", "DELETE", "/documents/{minimal}")
    capture.record("patch_deleted", "PATCH", "/documents/{minimal}", body={"title": "ignored"})
    capture.record("list_deleted_excluded", "GET", "/documents")
    capture.create(
        "full",
        {
            "title": "Full Contract 知识库",
            "content": "合成正文 full document",
            "summary": "",
            "categoryId": "9007199254740993",
            "teamId": "9007199254740994",
            "authorId": "9007199254740995",
            "createBy": "9007199254740996",
            "coverImage": "https://example.invalid/cover.png",
            "tags": "rag,contract",
            "status": 1,
            "isPublic": True,
            "remark": "synthetic only",
        },
    )
    capture.create("archived", {"title": "Archived", "content": "archive", "status": 2})
    capture.record("get_full", "GET", "/documents/{full}")
    capture.record(
        "list_combined_filters",
        "GET",
        "/documents?categoryId=9007199254740993"
        "&teamId=9007199254740994&authorId=9007199254740995&status=1&title=contract",
    )
    capture.record("list_page_two", "GET", "/documents?page=2&pageSize=1")
    capture.record("list_title_casefold", "GET", "/documents?title=FULL%20CONTRACT")
    capture.record("list_title_cjk", "GET", "/documents?title=%E7%9F%A5%E8%AF%86%E5%BA%93")
    capture.record(
        "patch_optional_null",
        "PATCH",
        "/documents/{full}",
        body={"summary": None, "categoryId": None, "remark": None},
    )
    capture.record("patch_empty_content", "PATCH", "/documents/{full}", body={"content": ""})
    capture.create("missing", {"title": "Missing body", "content": "will remove"})
    database.remove_content(capture.documents["missing"])
    capture.record("missing_content_detail", "GET", "/documents/{missing}")
    capture.record(
        "missing_content_patch", "PATCH", "/documents/{missing}", body={"content": "new body"}
    )
