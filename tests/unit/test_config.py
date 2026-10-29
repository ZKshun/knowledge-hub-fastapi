import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from knowledge_hub.core import config
from knowledge_hub.core.config import Settings

ENV_KEYS = (
    "PORT",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "MONGO_URI",
    "SNOWFLAKE_WORKER_ID",
    "SNOWFLAKE_OFFSET",
)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_KEYS:
        monkeypatch.delenv(name, raising=False)


def test_legacy_environment_names_are_read_at_explicit_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "PORT": "8011",
        "POSTGRES_HOST": "db",
        "POSTGRES_PORT": "55432",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "sample-password",
        "POSTGRES_DB": "knowledge_hub_fastapi_test",
        "MONGO_URI": "mongodb://user:sample-password@localhost:57017/test?authSource=admin",
        "SNOWFLAKE_WORKER_ID": "1023",
        "SNOWFLAKE_OFFSET": "1704067200123",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    settings = Settings()
    assert (settings.port, settings.postgres_host, settings.postgres_port) == (8011, "db", 55432)
    assert (settings.postgres_user, settings.postgres_db) == (
        "test_user",
        "knowledge_hub_fastapi_test",
    )
    assert settings.postgres_password.get_secret_value() == "sample-password"
    assert settings.mongo_uri.get_secret_value() == values["MONGO_URI"]
    assert (settings.snowflake_worker_id, settings.snowflake_offset) == (1023, 1704067200123)


def test_no_dotenv_is_implicitly_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("PORT=8123\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert Settings().port == 8000
    assert Settings(_env_file=tmp_path / ".env").port == 8123


def test_import_does_not_construct_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "invalid-port")
    importlib.reload(config)
    with pytest.raises(ValidationError):
        config.Settings()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PORT", "0"),
        ("PORT", "65536"),
        ("POSTGRES_PORT", "0"),
        ("POSTGRES_HOST", ""),
        ("POSTGRES_USER", ""),
        ("POSTGRES_DB", ""),
        ("POSTGRES_PASSWORD", ""),
        ("SNOWFLAKE_WORKER_ID", "-1"),
        ("SNOWFLAKE_WORKER_ID", "1024"),
        ("SNOWFLAKE_OFFSET", "-1"),
        ("MONGO_URI", "https://user:never-print-this@host/test"),
    ],
)
def test_invalid_environment_fails_without_exposing_input(
    name: str, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError) as failure:
        Settings()
    assert "never-print-this" not in str(failure.value)


def test_credentials_are_redacted_and_values_cannot_be_reassigned() -> None:
    settings = Settings(
        postgres_password="sample-secret", mongo_uri="mongodb+srv://u:sample-secret@db/test"
    )
    assert "sample-secret" not in repr(settings)
    assert "sample-secret" not in settings.model_dump_json()
    with pytest.raises(ValidationError):
        settings.port = 9000
