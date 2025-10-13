from typing import Mapping

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tgbot.services.locales import (
    BUTTON_KEYS,
    START_MESSAGE_KEY,
)


class TenantLocaleAction(CallbackData, prefix="tlc"):
    action: str
    key: str


def main_keyboard(locales: Mapping[str, object]):
    markup = InlineKeyboardBuilder()

    for key in BUTTON_KEYS:
        locale = locales.get(key)
        if not locale:
            continue
        text = getattr(locale, "name", str(key))
        markup.button(text=text, callback_data=key)

    markup.adjust(1)
    return markup.as_markup()


def tenant_locale_admin_keyboard(locales: Mapping[str, object]):
    markup = InlineKeyboardBuilder()

    start_locale = locales.get(START_MESSAGE_KEY)
    start_label = getattr(start_locale, "name", "Приветствие")
    markup.button(
        text=f"📝 {start_label}",
        callback_data=TenantLocaleAction(action="text", key=START_MESSAGE_KEY).pack(),
    )

    for key in BUTTON_KEYS:
        locale = locales.get(key)
        if not locale:
            continue
        name = getattr(locale, "name", key)
        markup.button(
            text=f"🔤 Кнопка: {name}",
            callback_data=TenantLocaleAction(action="name", key=key).pack(),
        )
        markup.button(
            text=f"💬 Ответ: {name}",
            callback_data=TenantLocaleAction(action="text", key=key).pack(),
        )

    markup.adjust(1)
    return markup.as_markup()


