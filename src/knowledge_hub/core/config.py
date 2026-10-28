from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=True,
        populate_by_name=True,
        frozen=True,
        hide_input_in_errors=True,
    )

    port: int = Field(default=8000, ge=1, le=65535, validation_alias="PORT")
    postgres_host: str = Field(default="localhost", min_length=1, validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, ge=1, le=65535, validation_alias="POSTGRES_PORT")
    postgres_user: str = Field(default="user", min_length=1, validation_alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(
        default=SecretStr("123456"), min_length=1, validation_alias="POSTGRES_PASSWORD"
    )
    postgres_db: str = Field(default="knowledge_hub", min_length=1, validation_alias="POSTGRES_DB")
    mongo_uri: SecretStr = Field(
        default=SecretStr(
            "mongodb://mongo_user:mongo_pass123@localhost:27017/knowledge_hub?authSource=admin"
        ),
        validation_alias="MONGO_URI",
    )
    snowflake_worker_id: int = Field(
        default=1, ge=0, le=1023, validation_alias="SNOWFLAKE_WORKER_ID"
    )
    snowflake_offset: int = Field(default=1704067200000, ge=0, validation_alias="SNOWFLAKE_OFFSET")

    @field_validator("mongo_uri")
    @classmethod
    def validate_mongo_scheme(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("MONGO_URI must use mongodb:// or mongodb+srv://")
        return value
