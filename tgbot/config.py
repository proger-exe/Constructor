from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    # env/runtime
    env: str = Field("prod", validation_alias="ENV")  # dev|stage|prod
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    # http server (aiohttp webhook)
    http_host: str = Field("0.0.0.0", validation_alias="HTTP_HOST")
    http_port: int = Field(8080, validation_alias="HTTP_PORT")

    # features
    use_redis: bool = Field(True, validation_alias="USE_REDIS")

    # external base url for webhooks (https)
    external_base_url: str = Field(..., validation_alias="EXTERNAL_BASE_URL")

    # Vault
    vault_addr: str = Field(..., validation_alias="VAULT_ADDR")
    vault_token: Optional[str] = Field(None, validation_alias="VAULT_TOKEN")
    vault_role_id: Optional[str] = Field(None, validation_alias="VAULT_ROLE_ID")
    vault_secret_id: Optional[str] = Field(None, validation_alias="VAULT_SECRET_ID")
    vault_kv_mount: str = Field("kv", validation_alias="VAULT_KV_MOUNT")
    vault_ttl_seconds: int = Field(60, validation_alias="VAULT_TTL_SECONDS")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
    }

    @field_validator("env")
    @classmethod
    def _normalize_env(cls, v: str) -> str:
        return (v or "").lower()


class RuntimeSecrets(BaseModel):
    webhook_secret: Optional[str] = None
    db_dsn: Optional[str] = None
    redis_dsn: Optional[str] = None
    main_bot_token: Optional[str] = None
    admin_ids: list[int] = Field(default_factory=list)
