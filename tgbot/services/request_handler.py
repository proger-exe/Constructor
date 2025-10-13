import secrets as _secrets
from typing import Any, Dict, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import BaseRequestHandler
from aiohttp import web
from aiohttp.abc import Application

from tgbot.common.logging_setup import log
from tgbot.common.logging_setup import tenant_id_var as ctx_tenant
from tgbot.database.managers import TenantManager
from tgbot.services.tenants import TenantService


class UUIDBasedRequestHandler(BaseRequestHandler):
    """
    Multi-tenant webhook handler:
    - Tenant is determined by {uid} in the URL path.
    - Bot token is loaded from Vault via TenantService (cached).
    - Keeps tenant_id context var set for the WHOLE request handling,
      so downstream logs (e.g., aiogram.event) include tenant_id.
    """

    def __init__(
        self,
        dispatcher: Dispatcher,
        tenant_service: TenantService,
        *,
        handle_in_background: bool = True,
        secret_token: Optional[str] = None,
        bot_settings: Optional[Dict[str, Any]] = None,
        **data: Any,
    ) -> None:
        super().__init__(
            dispatcher=dispatcher, handle_in_background=handle_in_background, **data
        )
        self.secret_token = secret_token
        self.bot_settings = bot_settings or {}
        self.tenant_service = tenant_service
        # Bot instances cache: tenant_uid -> Bot
        self.bots: Dict[str, Bot] = {}

    def verify_secret(self, telegram_secret_token: str, bot: Bot) -> bool:
        """
        Validate Telegram 'X-Telegram-Bot-Api-Secret-Token' header.
        If no secret is configured, allow all (useful for dev).
        """
        return (
            True
            if not self.secret_token
            else _secrets.compare_digest(telegram_secret_token or "", self.secret_token)
        )

    def register(self, app: Application, /, path: str, **kwargs: Any) -> None:
        """
        Register this handler in aiohttp with a path that MUST contain {uid}.
        Also attach cleanup to close cached Bot sessions on shutdown.
        """
        if "{uid}" not in path:
            raise ValueError("Path should contain '{uid}' substring")
        super().register(app, path=path, **kwargs)

        async def _cleanup(_app: Application):
            for bot in self.bots.values():
                await bot.session.close()

        app.on_cleanup.append(_cleanup)

    async def handle(self, request: web.Request) -> web.StreamResponse:
        """
        Entry point called by aiohttp for each webhook request.
        We set tenant_id context var here and keep it until the whole
        processing is done (including aiogram dispatch & logging).
        """
        uid = request.match_info.get("uid")
        token = ctx_tenant.set(uid)  # keep tenant in context for the whole request
        try:
            return await super().handle(request)
        finally:
            # Reset AFTER aiogram finished processing and logging
            ctx_tenant.reset(token)

    async def resolve_bot(self, request: web.Request) -> Bot:
        """
        Resolve/create a Bot for the given tenant UID:
        - Check tenant exists and is active in DB
        - Load bot token from Vault via TenantService (async, cached)
        - Recreate Bot if token has changed (rotation)
        """
        uid = request.match_info["uid"]

        # Ensure tenant exists and is active
        tenant = await TenantManager.get_by_uid(uid)
        if not tenant or not getattr(tenant, "is_active", True):
            log.warning("tenant_not_found", extra={"tenant_uid": uid})
            raise web.HTTPNotFound(text="Tenant not found")

        # Load token (cache first, Vault on miss)
        ctx = await self.tenant_service.get_context(uid)

        # Reuse or recreate Bot if token rotated
        bot = self.bots.get(uid)
        if bot is None or bot.token != ctx.bot_token:
            if bot is not None:
                await bot.session.close()
            bot = Bot(
                token=ctx.bot_token,
                default=DefaultBotProperties(parse_mode="HTML"),
            )
            self.bots[uid] = bot

        log.info("tenant_resolved", extra={"tenant_uid": uid})
        return bot

    async def close(self) -> None:
        for bot in self.bots.values():
            await bot.session.close()
