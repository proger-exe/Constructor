from typing import Iterable, Set

from aiogram.filters import Filter
from aiogram.types import TelegramObject, User


class AdminFilter(Filter):
    """Admin filter for MAIN bot.
    Should be set up on admin_router/main_dp.
    """

    def __init__(self, admin_ids: Iterable[int]):
        self.admin_ids: Set[int] = {int(x) for x in admin_ids}

    async def __call__(self, event: TelegramObject) -> bool:
        from_user: User | None = getattr(event, "from_user", None)
        return bool(from_user and from_user.id in self.admin_ids)
