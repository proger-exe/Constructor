import asyncio
import contextlib

import aiohttp_cors
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from aiohttp.web_app import Application

from tgbot.bootstrap import load_settings
from tgbot.common.logging_setup import log
from tgbot.config import RuntimeSecrets
from tgbot.filters.admin import AdminFilter
from tgbot.handlers import (
    user_router,
    tenant_admin_router,
    user_tenant_router,
)
from tgbot.middlewares.context import ContextLoggingMiddleware
from tgbot.services.request_handler import UUIDBasedRequestHandler


def register_all_handlers(dp: Dispatcher, secrets: RuntimeSecrets):
    # DI + контекст + БД
    dp.update.middleware(ContextLoggingMiddleware())

    # Фильтры
    tenant_admin_router.message.filter(AdminFilter(secrets.admin_ids))
    tenant_admin_router.callback_query.filter(AdminFilter(secrets.admin_ids))

    dp.include_routers(
        user_router
    )


def register_tenant_handlers(dp: Dispatcher, secrets: RuntimeSecrets):
    # DI + контекст + БД

    dp.update.middleware(ContextLoggingMiddleware())

    dp.include_routers(
        user_tenant_router,
        tenant_admin_router
    )


async def create_app() -> Application:
    app, secrets, _vault, tenant_service = load_settings()

    # DB init
    # if secrets.db_dsn:
    #     await init_engine(secrets.db_dsn)

    webapp = web.Application()
    webapp["settings"] = app
    webapp["secrets"] = secrets
    webapp["vault"] = _vault
    webapp["tenant_service"] = tenant_service

    cors = aiohttp_cors.setup(
        webapp,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_methods=["GET", "POST", "PUT", "DELETE"],
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        },
    )

    main_bot = Bot(
        token=secrets.main_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    main_dp = Dispatcher()

    register_all_handlers(main_dp, secrets)

    main_handler = SimpleRequestHandler(
        dispatcher=main_dp,
        bot=main_bot,
        secret_token=secrets.webhook_secret,
    )
    main_handler.register(webapp, path="/webhook/main")

    # Multi-Tenant webhook
    tenant_dp = Dispatcher()

    register_tenant_handlers(tenant_dp, secrets)

    tenant_handler = UUIDBasedRequestHandler(
        dispatcher=tenant_dp,
        tenant_service=tenant_service,
        secret_token=secrets.webhook_secret,
        bot_settings={"default": DefaultBotProperties(parse_mode=ParseMode.HTML)},
        # session_factory=db_core.Session,
    )
    tenant_handler.register(webapp, path="/webhook/{uid}")


    async def on_startup(_):
        main_url = f"{app.external_base_url}/webhook/main"
        await main_bot.set_webhook(
            url=main_url,
            secret_token=secrets.webhook_secret,
            drop_pending_updates=True,
        )
        log.info("main_webhook_set", extra={"url": main_url})

    async def on_cleanup(_):
        # останавливаем фон
        task = webapp.get("cleanup_task")
        if task:
            task.cancel()
            with contextlib.suppress(Exception):
                await task
        fx_task = webapp.get("fx_task")  # <-- ДОБАВЛЕНО
        if fx_task:
            fx_task.cancel()
            with contextlib.suppress(Exception):
                await fx_task
        await main_bot.session.close()
        for dp_bot in tenant_handler.bots.values():
            await dp_bot.session.close()

    webapp.on_startup.append(on_startup)
    webapp.on_cleanup.append(on_cleanup)

    log.info("http_ready", extra={"host": app.http_host, "port": app.http_port})
    return webapp


async def main():
    app = await create_app()
    settings = app["settings"]

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.http_host, port=settings.http_port)
    await site.start()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
