# Multi-Tenant Telegram Bot

This is a multi-tenant Telegram bot service built with **Aiogram**, **Aiohttp**, and **HashiCorp Vault**.  
It allows managing multiple tenant bots dynamically — tokens are stored securely in Vault, fetched on demand, and webhooks are set automatically.

---

## 📌 Features

- **Multi-tenant**: Each bot (tenant) has its own token and webhook endpoint.
- **Secure secret storage**: All tokens, DB DSNs, and other secrets are in Vault KV v2.
- **Webhook validation**: Incoming requests validated with `X-Telegram-Bot-Api-Secret-Token`.
- **Tenant cache**: Tokens are cached in memory for a configurable TTL.
- **Per-tenant isolation**: Each webhook request resolves its own bot instance.
- **Dynamic bot registration**: Add/remove tenants at runtime.

# Vault Structure
> All secrets are stored in KV v2 under the `kv` mount.
> 
```
kv/
└── tgbot/
    ├── common/
    │   ├── webhook_secret               # value stored under key "webhook_secret"
    │   ├── db_dsn                       # value stored under key "db_dsn"
    │   └── redis_dsn                    # value stored under key "redis_dsn" (optional)
    ├── main_bot                         # (optional) a single doc with multiple keys
    │   └── { bot_token, admin_ids }
    └── tenants/
        └── <tenant_uid>                 # one doc per tenant with "bot_token"
```