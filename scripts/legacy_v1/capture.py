import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import httpx

from tests.contract.comparison import normalize_response

TIME_PATTERN = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?P<fraction>\.\d+)?(?P<zone>Z|\+00:00)?")


class DatabaseProbe(Protocol):
    def snapshot(self) -> dict[str, object]: ...


class CaptureSession:
    def __init__(self, http: httpx.Client, probe: DatabaseProbe, output: Path) -> None:
        self.http = http
        self.probe = probe
        self.output = output
        self.documents: dict[str, str] = {}
        self.records: list[str] = []
        self.bindings: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    def record(
        self,
        name: str,
        method: str,
        path: str,
        *,
        body: dict[str, object] | None = None,
    ) -> object:
        filename = f"{len(self.records) + 1:03d}_{name}.json"
        target = self.output / filename
        if target.exists():
            raise FileExistsError(f"Evidence already exists: {filename}")
        response = self.http.request(method, path.format_map(self.documents), json=body)
        payload: object = response.json()
        record: dict[str, object] = {
            "request": {"method": method, "path": path, "body": body},
            "response": {
                "status": response.status_code,
                "contentType": response.headers.get("content-type"),
                "body": payload,
            },
            "state": self.probe.snapshot(),
        }
        self._bind_generated_values(record)
        record["normalized"] = normalize_response(record, self.bindings)
        self.output.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(record, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
        self.records.append(filename)
        return payload

    def create(self, name: str, body: dict[str, object]) -> str:
        result = self.record(f"create_{name}", "POST", "/documents", body=body)
        document_id = result.get("id") if isinstance(result, dict) else None
        if not isinstance(document_id, str):
            raise ValueError(f"Expected successful create for {name}, got {result!r}")
        self.documents[name] = document_id
        return document_id

    def _bind(self, value: str, kind: str) -> None:
        if value not in self.bindings:
            self._counts[kind] = self._counts.get(kind, 0) + 1
            self.bindings[value] = f"@{kind}:{self._counts[kind]}"
            if kind == "time" and (match := TIME_PATTERN.fullmatch(value)):
                precision = len((match["fraction"] or "").lstrip("."))
                self.bindings[value] += (
                    f";precision={precision};timezone={match['zone'] or 'naive'}"
                )

    def _bind_generated_values(self, value: object) -> None:
        if isinstance(value, list):
            for item in value:
                self._bind_generated_values(item)
        elif isinstance(value, Mapping):
            for key, item in value.items():
                if isinstance(item, str):
                    self._bind_field(str(key), item)
                self._bind_generated_values(item)

    def _bind_field(self, key: str, value: str) -> None:
        if key == "message":
            match = re.fullmatch(r"Document (?:content )?([0-9a-f]+) not found", value)
            if match and match[1] in self.bindings:
                self.bindings[value] = value.replace(match[1], self.bindings[match[1]], 1)
        if key in {"id", "documentId"} and re.fullmatch(r"[0-9]{1,19}", value):
            self._bind(value, "document")
        elif key in {"contentId", "content_id", "_id"} and re.fullmatch("[0-9a-f]{24}", value):
            self._bind(value, "content")
        elif key in {
            "createdAt",
            "updatedAt",
            "publishTime",
            "created_at",
            "updated_at",
            "publish_time",
        } and TIME_PATTERN.fullmatch(value):
            self._bind(value, "time")
