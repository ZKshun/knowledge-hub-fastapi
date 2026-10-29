from fastapi import FastAPI

from knowledge_hub.modules.documents.api.router import router


def register_routes(app: FastAPI) -> None:
    app.include_router(router)
