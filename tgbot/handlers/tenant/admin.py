from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery, Message

from tgbot.filters.tenant_admin import TenantAdminFilter
from tgbot.keyboards.tenant.inline import (
    TenantLocaleAction,
    TenantAdminAction,
    main_keyboard,
    tenant_locale_admin_keyboard,
)
from tgbot.services.context import get_current_tenant
from tgbot.services.locales import (
    BUTTON_KEYS,
    START_MESSAGE_KEY,
    TenantLocaleService,
)
from tgbot.services.settings import TenantSettingsService
from tgbot.database.models import TenantUser


class LocaleEditState(StatesGroup):
    waiting_for_value = State()


class SubscriptionState(StatesGroup):
    waiting_for_channel = State()


class BroadcastState(StatesGroup):
    waiting_for_message = State()


admin_router = Router(name="tenant_admin")
admin_router.message.filter(TenantAdminFilter())
admin_router.callback_query.filter(TenantAdminFilter())


async def _get_locale_service() -> TenantLocaleService:
    tenant = await get_current_tenant()
    return TenantLocaleService(tenant_id=tenant.numeric_id)


async def _get_settings_service() -> TenantSettingsService:
    tenant = await get_current_tenant()
    return TenantSettingsService(tenant_id=tenant.numeric_id)


async def _get_subscription_summary(
    settings_service: TenantSettingsService | None = None,
) -> tuple[str, bool]:
    if settings_service is None:
        settings_service = await _get_settings_service()
    subscription = await settings_service.get_subscription_config()
    if not subscription.required:
        return "обязательная подписка отключена", False

    username = subscription.normalized_username
    if username and username.startswith("-"):
        channel_display = username
    elif username:
        channel_display = f"@{username}"
    else:
        channel_display = "не задан"
    return f"обязательная подписка включена (канал: {channel_display})", True


async def _send_admin_panel(message: Message) -> None:
    tenant = await get_current_tenant()
    locale_service = TenantLocaleService(tenant_id=tenant.numeric_id)
    settings_service = TenantSettingsService(tenant_id=tenant.numeric_id)
    locales = await locale_service.get_locales((START_MESSAGE_KEY, *BUTTON_KEYS))
    subscription_summary, subscription_enabled = await _get_subscription_summary(
        settings_service
    )
    subscribers = await TenantUser.filter(tenant_id=tenant.numeric_id).count()

    start_locale = locales[START_MESSAGE_KEY]
    await message.answer(
        (
            "Панель управления контентом.\n"
            f"Текущее приветствие:\n{start_locale.text}\n\n"
            f"Статус подписки: {subscription_summary}.\n"
            f"Подписчиков: {subscribers}"
        ),
        reply_markup=tenant_locale_admin_keyboard(
            locales, subscription_enabled=subscription_enabled
        ),
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


@admin_router.callback_query(TenantAdminAction.filter())
async def handle_admin_action(
    call: CallbackQuery, callback_data: TenantAdminAction, state: FSMContext
) -> None:
    action = callback_data.action

    if action == "subscription":
        await state.set_state(SubscriptionState.waiting_for_channel)
        subscription_summary, _ = await _get_subscription_summary()
        await call.message.answer(
            "Введите username канала без пробелов (например, @mychannel).\n"
            "Отправьте 0 или 'отмена' для отключения обязательной подписки.\n"
            f"Текущий статус: {subscription_summary}."
        )
    elif action == "broadcast":
        await state.set_state(BroadcastState.waiting_for_message)
        await call.message.answer(
            "Отправьте сообщение для рассылки всем пользователям этого тенанта.\n"
            "Допустимо переслать медиасообщение. Для отмены напишите 'отмена'."
        )

    await call.answer()


def _normalize_channel_input(raw_value: str) -> str | None:
    value = raw_value.strip()
    if not value:
        return None
    lowered = value.lower()
    if lowered in {"0", "отмена", "cancel", "disable", "none"}:
        return None
    if value.startswith("https://t.me/"):
        value = value.split("https://t.me/", maxsplit=1)[1]
    elif value.startswith("http://t.me/"):
        value = value.split("http://t.me/", maxsplit=1)[1]
    elif value.startswith("t.me/"):
        value = value.split("t.me/", maxsplit=1)[1]
    if value.startswith("@"):
        value = value[1:]
    value = value.strip()
    if not value:
        return None
    if "+" in value:
        raise ValueError("Пожалуйста, укажите публичный @username канала, а не пригласительную ссылку.")
    if any(ch.isspace() for ch in value):
        raise ValueError("Имя канала не должно содержать пробелов.")
    return value


@admin_router.message(SubscriptionState.waiting_for_channel)
async def save_subscription_settings(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Необходимо отправить текстовое сообщение.")
        return

    text = message.text.strip()
    if text.lower() in {"отмена", "/cancel"}:
        await state.clear()
        await message.answer("Настройка обязательной подписки отменена.")
        return

    try:
        channel_username = _normalize_channel_input(text)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    try:
        settings_service = await _get_settings_service()
    except LookupError:
        await state.clear()
        await message.answer("Не удалось определить текущий тенант.")
        return

    subscription = await settings_service.update_subscription(channel_username)
    if subscription.required:
        await message.answer(
            "Обязательная подписка включена."
            f" Канал: @{subscription.normalized_username}."
        )
    else:
        await message.answer("Обязательная подписка отключена.")

    await state.clear()
    await _send_admin_panel(message)


@admin_router.message(BroadcastState.waiting_for_message)
async def send_broadcast(message: Message, state: FSMContext) -> None:
    if message.text and message.text.lower() in {"отмена", "/cancel"}:
        await state.clear()
        await message.answer("Рассылка отменена.")
        return

    try:
        tenant = await get_current_tenant()
    except LookupError:
        await state.clear()
        await message.answer("Не удалось определить текущий тенант.")
        return

    user_ids = await TenantUser.filter(tenant_id=tenant.numeric_id).values_list("tg_id", flat=True)
    if not user_ids:
        await state.clear()
        await message.answer("Нет пользователей для рассылки.")
        await _send_admin_panel(message)
        return

    sent = 0
    failed = 0
    for user_id in user_ids:
        try:
            await message.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            sent += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1

    await state.clear()
    await message.answer(
        "Рассылка завершена."
        f" Отправлено: {sent}."
        f" Ошибок: {failed}."
    )
    await _send_admin_panel(message)


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
