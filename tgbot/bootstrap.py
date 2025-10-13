from typing import Tuple

from tgbot.common.logging_setup import log, setup_logging
from tgbot.config import AppSettings, RuntimeSecrets
from tgbot.filters.tenant_admin import set_tenant_admin_ids
from tgbot.services.tenants import TenantService
from tgbot.services.vault import VaultClient

KV_MAIN_BOT = "tgbot/main_bot"
KV_WEBHOOK_SECRET = "tgbot/common/webhook_secret"
KV_DB_DSN = "tgbot/common/db_dsn"
KV_REDIS_DSN = "tgbot/common/redis_dsn"


def load_settings() -> Tuple[AppSettings, RuntimeSecrets, VaultClient, TenantService]:
    app = AppSettings()
    setup_logging(app.log_level)

    secrets = RuntimeSecrets()
    vault = VaultClient(
        addr=app.vault_addr,
        token=app.vault_token,
        role_id=app.vault_role_id,
        secret_id=app.vault_secret_id,
        mount=app.vault_kv_mount,
        ttl=app.vault_ttl_seconds,
    )

    # global/common secrets
    secrets.webhook_secret = vault.read_kv(KV_WEBHOOK_SECRET).get("webhook_secret")
    secrets.db_dsn = vault.read_kv(KV_DB_DSN).get("db_dsn")
    secrets.redis_dsn = vault.read_kv(KV_REDIS_DSN).get("redis_dsn")

    # main bot
    main = vault.read_kv(KV_MAIN_BOT)
    secrets.main_bot_token = main.get("bot_token")

    raw_admins = main.get("admin_ids", [])
    # Allowed formats: [123, 456] or "123,456"
    if isinstance(raw_admins, str):
        admin_ids = [int(x) for x in raw_admins.split(",") if x.strip()]
    else:
        admin_ids = [int(x) for x in raw_admins]

    secrets.admin_ids = admin_ids
    set_tenant_admin_ids(admin_ids)

    missing = []
    if app.env == "prod":
        if not secrets.webhook_secret:
            missing.append("Vault:tgbot/common.webhook_secret")
        if not secrets.db_dsn:
            missing.append("Vault:tgbot/common.db_dsn")
        if app.use_redis and not secrets.redis_dsn:
            missing.append("Vault:tgbot/common.redis_dsn")
        if not secrets.main_bot_token:
            missing.append("Vault:tgbot/main_bot.bot_token")
        if missing:
            raise RuntimeError("Missing required secrets: " + ", ".join(missing))

    log.info("bootstrap_ok", extra={"env": app.env})
    tenant_service = TenantService(vault, ttl_seconds=app.vault_ttl_seconds)
    return app, secrets, vault, tenant_service
