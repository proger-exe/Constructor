"""Database models management module."""

import logging
from datetime import datetime
from typing import Any, Coroutine, List, Optional

from tortoise.exceptions import IntegrityError, OperationalError

from tgbot.database.models import Tenant, TenantLocale, User

logger = logging.getLogger("managers")


class UserManager:
    "Basic user manager class."

    def __init__(self, user_id: int) -> None:
        """Initializing the class with the given values.

        Args:
            user_id (int): The user identifier to work with.
        """
        self.user_id = user_id

    async def create(self) -> User:
        """Creates user instance."""
        try:
            user = await User.create(
                tg_id=self.user_id,
            )
            return user
        except IntegrityError as e:
            if "duplicate" in str(e):
                user = await User.filter(tg_id=self.user_id).first()
                return user
            logger.warning("IntegrityError: %s", e)

    async def get(self) -> User:
        """Gets a user from the database."""
        try:
            user = await User.filter(tg_id=self.user_id).first()
            return user
        except OperationalError as e:
            logger.warning("Could not get user due to %s", e)
            return None

    async def get_ban(self) -> bool:
        """Gets user ban status from the database."""
        try:
            user = await User.filter(tg_id=self.user_id).first()
            return user.ban
        except OperationalError as e:
            logger.warning("Could not get user ban due to %s", e)
            return False

    @staticmethod
    async def get_all() -> None | list[Any] | tuple[Any, ...]:
        """Gets all users IDs from the database.

        Returns:
            list[int]: A list of IDs.
        """
        try:
            users = await User.all().values_list("tg_id", flat=True)
            return users
        except OperationalError as e:
            logger.error("Empty database %s", e)

    async def get_days(self) -> int:
        """Get user days by its ID.

        Returns:
            int: The amount of days.
        """
        try:
            today = datetime.today()
            user = await User.filter(tg_id=self.user_id).first()
            delta = today - user.register_date
            return delta.days
        except OperationalError as e:
            logger.warning("DoesNotExist: %s", e)

    async def update_balance(self, amount: float) -> None:
        """Updates user's balance with the given amount.

        Args:
            amount (float): Amount to update.
        """
        try:
            user = await User.filter(tg_id=self.user_id).first()
            amnew = user.balance + float(amount)
            await User.filter(tg_id=self.user_id).update(balance=amnew)
        except OperationalError as e:
            logger.warning("Could not update user balance due to %s", e)

    async def ban(self) -> None:
        """Bans user."""
        try:
            await User.filter(tg_id=self.user_id).update(ban=True)
        except OperationalError as e:
            logger.warning("Could not ban user %s", e)

    async def unban(self) -> None:
        """Unbans user."""
        try:
            await User.filter(tg_id=self.user_id).update(ban=False)
        except OperationalError as e:
            logger.warning("Could not unban user %s", e)


class TenantManager:
    """DB manager for working with Tenants."""

    def __init__(self, owner_id: int):
        self.owner_id = owner_id

    async def create(self, uid: str, name: str | None = None) -> Optional[Tenant]:
        try:
            return await Tenant.create(owner_id=self.owner_id, uuid=uid, name=name)
        except IntegrityError as e:
            logger.warning("IntegrityError on tenant.create: %s", e)
            return None

    async def get(self) -> Optional[Tenant]:
        try:
            return await Tenant.filter(owner_id=self.owner_id).first()
        except OperationalError as e:
            logger.warning("Could not get tenant due to %s", e)
            return None

    async def get_all(self) -> List[Tenant] | None:
        try:
            return await Tenant.filter(owner_id=self.owner_id).all()
        except OperationalError as e:
            logger.warning("Could not get all tenants due to %s", e)
            return None

    @staticmethod
    async def get_by_uid(uid: str) -> Optional[Tenant]:
        try:
            return await Tenant.filter(uuid=uid).first()
        except OperationalError as e:
            logger.warning("Could not get tenant by uid due to %s", e)
            return None

    @staticmethod
    async def delete(uid: str) -> None:
        try:
            await Tenant.filter(uuid=uid).delete()
        except OperationalError as e:
            logger.warning("Could not delete tenant due to %s", e)


class TenantLocaleManager:
    def __init__(self, locale_id: int):
        self.locale_id = locale_id
        self._cache: Optional["TenantLocale"] = None

    async def _ensure(self) -> "TenantLocale":
        if self._cache is None:
            self._cache = await TenantLocale.get(id=self.locale_id)
        return self._cache

    async def get_type(self) -> str:
        locale = await self._ensure()
        return locale.type

    async def get_label(self) -> str:
        locale = await self._ensure()
        return locale.name
    
    async def set_text(self, value) -> None:
        locale = await self._ensure()
        locale.text = value 
        await locale.save()

    
