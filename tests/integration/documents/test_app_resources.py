import pytest
from pymongo.errors import InvalidOperation, OperationFailure

from knowledge_hub.app import lifespan
from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings
from knowledge_hub.integrations.mongodb.client import MongoDatabase
from knowledge_hub.integrations.postgres.database import PostgresDatabase


def settings():
    return Settings(
        _env_file=None,
        port=8000,
        postgres_host="127.0.0.1",
        postgres_port=55432,
        postgres_user="kh_test",
        postgres_password="local-contract-only",
        postgres_db="knowledge_hub_fastapi_test",
        mongo_uri="mongodb://127.0.0.1:57017/knowledge_hub_fastapi_test",
        snowflake_worker_id=1,
        snowflake_offset=1704067200000,
    )


def tracked_clients(storage, monkeypatch, failure):
    resources = {}

    class ScopedPostgres(PostgresDatabase):
        def __init__(self, config):
            super().__init__(config, schema=storage.schema)
            resources["postgres"] = self
            resources["pools"] = (self.engine.pool, self.lock_engine.pool)
            self.disposed = False

        async def close(self):
            await super().close()
            self.disposed = True

    class ScopedMongo(MongoDatabase):
        def __init__(self, config):
            super().__init__(config)
            resources["mongo"] = self
            self.closed = False
            if failure == "startup":

                async def failed_ping(*args, **kwargs):
                    raise OperationFailure("synthetic startup ping failure")

                monkeypatch.setattr(self.database, "command", failed_ping)

        async def close(self):
            await super().close()
            self.closed = True

    monkeypatch.setattr(lifespan, "PostgresDatabase", ScopedPostgres)
    monkeypatch.setattr(lifespan, "MongoDatabase", ScopedMongo)
    return resources


@pytest.mark.parametrize("failure", [None, "startup", "running"])
async def test_lifespan_closes_real_mongo_and_both_postgres_pools(storage, monkeypatch, failure):
    resources = tracked_clients(storage, monkeypatch, failure)
    app = create_app(settings())

    async def run():
        async with app.router.lifespan_context(app):
            assert app.state.document_services.store is not None
            async with resources["postgres"].lock_engine.connect() as connection:
                await connection.exec_driver_sql("SELECT 1")
            if failure == "running":
                raise RuntimeError("synthetic lifespan failure")

    if failure == "startup":
        with pytest.raises(OperationFailure):
            await run()
    elif failure == "running":
        with pytest.raises(RuntimeError):
            await run()
    else:
        await run()
    assert resources["mongo"].closed and resources["postgres"].disposed
    assert all(pool.checkedout() == 0 for pool in resources["pools"])
    assert not hasattr(app.state, "document_services")
    with pytest.raises(InvalidOperation):
        await resources["mongo"].client.admin.command("ping")
