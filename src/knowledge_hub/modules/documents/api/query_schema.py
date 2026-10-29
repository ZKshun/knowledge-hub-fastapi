from typing import cast

from knowledge_hub.modules.documents.api.requests import DocumentQueryRequest


def query_parameters() -> list[dict[str, object]]:
    properties = cast(
        dict[str, dict[str, object]], DocumentQueryRequest.model_json_schema()["properties"]
    )
    return [
        {"name": name, "in": "query", "required": False, "schema": schema}
        for name, schema in properties.items()
    ]
