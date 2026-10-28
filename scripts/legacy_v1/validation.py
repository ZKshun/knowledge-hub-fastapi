from scripts.legacy_v1.capture import CaptureSession


def capture_validation(capture: CaptureSession) -> None:
    minimal: dict[str, object] = {"title": "Validation", "content": "synthetic content"}
    cases: list[tuple[str, dict[str, object]]] = [
        ("create_missing_fields", {}),
        ("create_missing_title", {"content": "body"}),
        ("create_title_number", {**minimal, "title": 123}),
        ("create_content_number", {**minimal, "content": 123}),
        ("create_unknown_field", {**minimal, "unexpected": "rejected"}),
        ("create_invalid_status", {**minimal, "status": 3}),
        ("create_status_string", {**minimal, "status": "1"}),
        ("create_boolean_string", {**minimal, "isPublic": "true"}),
        ("create_null_title", {**minimal, "title": None}),
        ("create_null_content", {**minimal, "content": None}),
        ("create_optional_null", {**minimal, "status": None, "isPublic": None, "summary": None}),
        ("create_empty_title", {**minimal, "title": ""}),
        ("create_empty_content", {**minimal, "content": ""}),
        ("create_whitespace_content", {**minimal, "content": " \t\r\n "}),
        ("create_unicode_boundary", {**minimal, "content": "a" * 199 + "🧠 tail"}),
        ("create_unicode_spaces", {**minimal, "content": "\ufeff\u00a0中，文\u2003hello\r\nworld"}),
        ("create_long_title", {**minimal, "title": "t" * 1024}),
    ]
    for name, body in cases:
        capture.record(name, "POST", "/documents", body=body)
    for name, query in [
        ("query_page_zero", "page=0"),
        ("query_page_negative", "page=-1"),
        ("query_size_too_large", "pageSize=101"),
        ("query_size_zero", "pageSize=0"),
        ("query_page_fraction", "page=1.5"),
        ("query_page_empty", "page="),
        ("query_status_empty", "status="),
        ("query_status_unknown", "status=999"),
        ("query_unknown", "unexpected=value"),
        ("query_wildcard", "title=%25"),
    ]:
        capture.record(name, "GET", f"/documents?{query}")
    patch_cases: list[tuple[str, dict[str, object]]] = [
        ("patch_unknown_field", {"unexpected": "rejected"}),
        ("patch_create_by_forbidden", {"createBy": "123"}),
        ("patch_null_title", {"title": None}),
        ("patch_null_content", {"content": None}),
        ("patch_null_status", {"status": None}),
        ("patch_null_public", {"isPublic": None}),
        ("patch_status_string", {"status": "1"}),
    ]
    for name, body in patch_cases:
        capture.record(name, "PATCH", "/documents/{full}", body=body)
    for name, identifier in [
        ("missing_id", "9223372036854775807"),
        ("malformed_id", "invalid"),
        ("overflow_id", "9223372036854775808"),
    ]:
        capture.record(name, "GET", f"/documents/{identifier}")
