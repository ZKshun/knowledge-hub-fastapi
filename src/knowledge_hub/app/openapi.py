from fastapi import FastAPI


def configure_openapi(app: FastAPI) -> None:
    schema = app.openapi()
    for path in schema["paths"].values():
        for operation in path.values():
            operation.get("responses", {}).pop("422", None)
    app.openapi_schema = schema
