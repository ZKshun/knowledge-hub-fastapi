import re

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from knowledge_hub.core.config import Settings


class Base(DeclarativeBase):
    pass


def postgres_url(settings: Settings) -> URL:
    return URL.create(
        "postgresql+asyncpg",
        username=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


def _engine(settings: Settings, schema: str) -> AsyncEngine:
    return create_async_engine(
        postgres_url(settings),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={
            "timeout": 10,
            "command_timeout": 10,
            "server_settings": {"timezone": "UTC", "search_path": schema},
        },
    )


class PostgresDatabase:
    def __init__(self, settings: Settings, *, schema: str = "public") -> None:
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
            raise ValueError("schema must be a simple PostgreSQL identifier")
        self.engine = _engine(settings, schema)
        # Waiting advisory locks must never consume the business pool's last connection.
        self.lock_engine = _engine(settings, schema)
        self.sessions = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def close(self) -> None:
        await self.lock_engine.dispose()
        await self.engine.dispose()
