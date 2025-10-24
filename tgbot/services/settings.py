from __future__ import annotations

from dataclasses import dataclass

from tgbot.database.models import TenantSettings


@dataclass(slots=True)
class SubscriptionConfig:
    required: bool
    channel_username: str | None

    @property
    def normalized_username(self) -> str | None:
        if not self.channel_username:
            return None
        return self.channel_username.lstrip("@")

    @property
    def channel_link(self) -> str | None:
        username = self.normalized_username
        if not username:
            return None
        if username.startswith("-"):
            return None
        return f"https://t.me/{username}"

    @property
    def chat_reference(self) -> str | None:
        """Return value suitable for get_chat_member call."""

        username = self.normalized_username
        if not username:
            return None
        if username.startswith("-") and username[1:].isdigit():
            return username
        return f"@{username}"


class TenantSettingsService:
    """Service for managing tenant-wide settings."""

    def __init__(self, tenant_id: int) -> None:
        self.tenant_id = tenant_id

    async def get_settings(self) -> TenantSettings:
        settings, _ = await TenantSettings.get_or_create(tenant_id=self.tenant_id)
        return settings

    async def get_subscription_config(self) -> SubscriptionConfig:
        settings = await self.get_settings()
        return SubscriptionConfig(
            required=settings.require_subscription and bool(settings.subscription_channel),
            channel_username=settings.subscription_channel,
        )

    async def update_subscription(self, channel_username: str | None) -> SubscriptionConfig:
        settings = await self.get_settings()
        settings.subscription_channel = channel_username
        settings.require_subscription = bool(channel_username)
        await settings.save()
        return await self.get_subscription_config()
