from __future__ import annotations

from typing import Dict, Iterable

from tgbot.database.models import TenantLocale

START_MESSAGE_KEY = "start-message"
FIRST_BUTTON_KEY = "first-button"
SECOND_BUTTON_KEY = "second-button"
THIRD_BUTTON_KEY = "third-button"
FOURTH_BUTTON_KEY = "four-button"

BUTTON_KEYS = (
    FIRST_BUTTON_KEY,
    SECOND_BUTTON_KEY,
    THIRD_BUTTON_KEY,
    FOURTH_BUTTON_KEY,
)

DEFAULT_LOCALES: Dict[str, Dict[str, str]] = {
    START_MESSAGE_KEY: {
        "name": "Приветственное сообщение",
        "text": "Привет!",
    },
    FIRST_BUTTON_KEY: {
        "name": "Первая кнопка",
        "text": "Ответ первой кнопки",
    },
    SECOND_BUTTON_KEY: {
        "name": "Вторая кнопка",
        "text": "Ответ второй кнопки",
    },
    THIRD_BUTTON_KEY: {
        "name": "Третья кнопка",
        "text": "Ответ третьей кнопки",
    },
    FOURTH_BUTTON_KEY: {
        "name": "Четвёртая кнопка",
        "text": "Ответ четвёртой кнопки",
    },
}


class TenantLocaleService:
    """Service for reading and mutating tenant-specific locales."""

    def __init__(self, tenant_id: int, lang: str = "ru") -> None:
        self.tenant_id = tenant_id
        self.lang = lang

    async def get_locale(self, key: str) -> TenantLocale:
        defaults = DEFAULT_LOCALES.get(key, {"name": key, "text": ""})
        locale, _ = await TenantLocale.get_or_create(
            tenant_id=self.tenant_id,
            type=key,
            lang=self.lang,
            defaults={
                "name": defaults.get("name", key),
                "text": defaults.get("text", ""),
            },
        )
        return locale

    async def get_locales(self, keys: Iterable[str]) -> Dict[str, TenantLocale]:
        result: Dict[str, TenantLocale] = {}
        for key in keys:
            result[key] = await self.get_locale(key)
        return result

    async def update_locale(
        self,
        key: str,
        *,
        name: str | None = None,
        text: str | None = None,
    ) -> TenantLocale:
        locale = await self.get_locale(key)
        if name is not None:
            locale.name = name
        if text is not None:
            locale.text = text
        await locale.save()
        return locale
