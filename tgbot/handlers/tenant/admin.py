from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from tgbot.filters.tenant_admin import TenantAdminFilter
from tgbot.keyboards.tenant.inline import (
    TenantLocaleAction,
    main_keyboard,
    tenant_locale_admin_keyboard,
)
from tgbot.services.context import get_current_tenant
from tgbot.services.locales import (
    BUTTON_KEYS,
    START_MESSAGE_KEY,
    TenantLocaleService,
)


class LocaleEditState(StatesGroup):
    waiting_for_value = State()


admin_router = Router(name="tenant_admin")
admin_router.message.filter(TenantAdminFilter())
admin_router.callback_query.filter(TenantAdminFilter())


async def _get_locale_service() -> TenantLocaleService:
    tenant = await get_current_tenant()
    return TenantLocaleService(tenant_id=tenant.numeric_id)


async def _send_admin_panel(message: Message) -> None:
    locale_service = await _get_locale_service()
    locales = await locale_service.get_locales((START_MESSAGE_KEY, *BUTTON_KEYS))

    start_locale = locales[START_MESSAGE_KEY]
    await message.answer(
        (
            "Панель управления контентом.\n"
            f"Текущее приветствие:\n{start_locale.text}"
        ),
        reply_markup=tenant_locale_admin_keyboard(locales),
    )


@admin_router.message(Command("admin"))
async def admin_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        await _send_admin_panel(message)
    except LookupError:
        await message.answer("Не удалось определить текущий тенант.")


@admin_router.callback_query(TenantLocaleAction.filter())
async def handle_locale_action(
    call: CallbackQuery, callback_data: TenantLocaleAction, state: FSMContext
) -> None:
    action = callback_data.action
    key = callback_data.key

    try:
        locale_service = await _get_locale_service()
        locale = await locale_service.get_locale(key)
    except LookupError:
        await call.answer()
        await call.message.answer("Не удалось определить текущий тенант.")
        return

    if action == "name":
        prompt = f"Введите новое название для кнопки «{locale.name}»"
    else:
        prompt = "Введите новый текст ответа"

    await state.update_data(key=key, action=action)
    await state.set_state(LocaleEditState.waiting_for_value)

    await call.message.answer(prompt)
    await call.answer()


@admin_router.message(LocaleEditState.waiting_for_value)
async def save_locale_update(message: Message, state: FSMContext) -> None:
    if message.text and message.text.lower() in {"отмена", "/cancel"}:
        await state.clear()
        await message.answer("Изменение отменено.")
        return

    data = await state.get_data()
    key = data.get("key")
    action = data.get("action")

    if not key or not action:
        await state.clear()
        await message.answer("Не удалось определить действие.")
        return

    try:
        locale_service = await _get_locale_service()
    except LookupError:
        await state.clear()
        await message.answer("Не удалось определить текущий тенант.")
        return

    value = message.html_text
    if value is None:
        await message.answer("Сообщение должно содержать текст.")
        return

    if action == "name":
        await locale_service.update_locale(key, name=value)
        await message.answer("Название кнопки обновлено.")
    else:
        await locale_service.update_locale(key, text=value)
        await message.answer("Текст ответа обновлён.")

    await state.clear()

    # Отображаем актуальные данные и клавиатуру для пользователя
    locales = await locale_service.get_locales((START_MESSAGE_KEY, *BUTTON_KEYS))
    await message.answer(
        "Клавиатура обновлена.",
        reply_markup=main_keyboard({key: locales[key] for key in BUTTON_KEYS}),
    )
    await _send_admin_panel(message)
