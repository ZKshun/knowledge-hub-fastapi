import argparse
from collections.abc import Sequence
from pathlib import Path

import uvicorn

from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings

app = create_app()


def run(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Knowledge Hub FastAPI service")
    parser.add_argument("--env-file", type=Path, default=None)
    args = parser.parse_args(argv)
    settings = Settings(_env_file=args.env_file)
    uvicorn.run(create_app(settings), host="127.0.0.1", port=settings.port, access_log=False)


if __name__ == "__main__":
    run()
