from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from tgbot.keyboards.tenant.inline import main_keyboard
from tgbot.services.context import get_current_tenant
from tgbot.services.locales import (
    BUTTON_KEYS,
    START_MESSAGE_KEY,
    TenantLocaleService,
)

user_tenant_router = Router(name="user_router")


async def _get_locale_service() -> TenantLocaleService:
    tenant = await get_current_tenant()
    return TenantLocaleService(tenant_id=tenant.numeric_id)


@user_tenant_router.message(CommandStart())
async def tenant_start_handler(message: Message):
    try:
        locale_service = await _get_locale_service()
    except LookupError:
        await message.answer("Не удалось определить текущий тенант.")
        return

    start_locale = await locale_service.get_locale(START_MESSAGE_KEY)
    button_locales = await locale_service.get_locales(BUTTON_KEYS)

    await message.answer(start_locale.text, reply_markup=main_keyboard(button_locales))


@user_tenant_router.callback_query(F.data.in_(BUTTON_KEYS))
async def answer_user(call: CallbackQuery):
    try:
        locale_service = await _get_locale_service()
    except LookupError:
        await call.answer()
        await call.message.answer("Не удалось определить текущий тенант.")
        return

    locale = await locale_service.get_locale(call.data)

    await call.answer()
    await call.message.answer(locale.text)
