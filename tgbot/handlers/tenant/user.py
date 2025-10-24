from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from tgbot.database.models import TenantUser
from tgbot.keyboards.tenant.inline import (
    CHECK_SUBSCRIPTION_CALLBACK,
    main_keyboard,
    subscription_keyboard,
)
from tgbot.services.context import get_current_tenant
from tgbot.services.locales import (
    BUTTON_KEYS,
    START_MESSAGE_KEY,
    TenantLocaleService,
)
from tgbot.services.settings import TenantSettingsService


user_tenant_router = Router(name="user_router")


async def _get_locale_service() -> TenantLocaleService:
    tenant = await get_current_tenant()
    return TenantLocaleService(tenant_id=tenant.numeric_id)


async def _get_settings_service() -> TenantSettingsService:
    tenant = await get_current_tenant()
    return TenantSettingsService(tenant_id=tenant.numeric_id)


async def _register_tenant_user(tenant_id: int, telegram_user) -> None:
    if telegram_user is None:
        return

    defaults = {
        "full_name": getattr(telegram_user, "full_name", None),
        "username": getattr(telegram_user, "username", None),
    }
    tenant_user, created = await TenantUser.get_or_create(
        tenant_id=tenant_id,
        tg_id=telegram_user.id,
        defaults=defaults,
    )
    if created:
        return

    updates = {}
    if tenant_user.full_name != defaults["full_name"]:
        updates["full_name"] = defaults["full_name"]
    if tenant_user.username != defaults["username"]:
        updates["username"] = defaults["username"]
    if updates:
        await TenantUser.filter(id=tenant_user.id).update(**updates)


async def _ensure_subscription(message: Message | CallbackQuery) -> bool:
    try:
        settings_service = await _get_settings_service()
    except LookupError:
        target = message.message if isinstance(message, CallbackQuery) else message
        await target.answer("Не удалось определить текущий тенант.")
        if isinstance(message, CallbackQuery):
            await message.answer()
        return False

    subscription = await settings_service.get_subscription_config()
    if not subscription.required:
        return True

    chat_reference = subscription.chat_reference
    if not chat_reference:
        return True

    telegram_user = message.from_user
    if telegram_user is None:
        return False

    try:
        member = await message.bot.get_chat_member(  # type: ignore[arg-type]
            chat_reference, telegram_user.id
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        member = None

    status = getattr(member, "status", None)
    is_member = status not in {"left", "kicked", None}

    if is_member:
        tenant = await get_current_tenant()
        await _register_tenant_user(tenant.numeric_id, telegram_user)
        return True

    link = subscription.channel_link
    target = message.message if isinstance(message, CallbackQuery) else message
    if link:
        await target.answer(
            "Для продолжения подпишитесь на канал, затем нажмите кнопку ниже.",
            reply_markup=subscription_keyboard(link),
        )
    else:
        await target.answer("Обязательная подписка включена, но ссылка не настроена.")

    if isinstance(message, CallbackQuery):
        await message.answer("Подписка не подтверждена", show_alert=True)
    return False


async def _send_start_content(message: Message) -> None:
    locale_service = await _get_locale_service()
    start_locale = await locale_service.get_locale(START_MESSAGE_KEY)
    button_locales = await locale_service.get_locales(BUTTON_KEYS)
    await message.answer(start_locale.text, reply_markup=main_keyboard(button_locales))


@user_tenant_router.message(CommandStart())
async def tenant_start_handler(message: Message):
    if not await _ensure_subscription(message):
        return

    tenant = await get_current_tenant()
    await _register_tenant_user(tenant.numeric_id, message.from_user)
    await _send_start_content(message)


@user_tenant_router.callback_query(F.data.in_(BUTTON_KEYS))
async def answer_user(call: CallbackQuery):
    if not await _ensure_subscription(call):
        return

    locale_service = await _get_locale_service()
    locale = await locale_service.get_locale(call.data)

    await call.answer()
    await call.message.answer(locale.text)


@user_tenant_router.callback_query(F.data == CHECK_SUBSCRIPTION_CALLBACK)
async def recheck_subscription(call: CallbackQuery):
    if await _ensure_subscription(call):
        await call.answer("Подписка подтверждена!", show_alert=True)
        await _send_start_content(call.message)
    else:
        await call.answer("Подписка не обнаружена", show_alert=True)
