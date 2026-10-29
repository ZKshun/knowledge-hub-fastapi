import json
from typing import Any

from starlette.responses import JSONResponse


class LegacyJSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

    def render(self, content: Any) -> bytes:
        # JavaScript JSON.stringify escapes lone UTF-16 surrogates instead of failing.
        return json.dumps(
            content, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
