from typing import Iterable, Set

from aiogram.filters import Filter
from aiogram.types import TelegramObject, User

TENANT_ADMIN_IDS: Set[int] = set()


def set_tenant_admin_ids(admin_ids: Iterable[int]) -> None:
    TENANT_ADMIN_IDS.clear()
    TENANT_ADMIN_IDS.update(int(x) for x in admin_ids)


class TenantAdminFilter(Filter):
    """Admin filter shared between tenant bots."""

    def __init__(self, admin_ids: Iterable[int] | None = None) -> None:
        if admin_ids is not None:
            self._local_admin_ids: Set[int] | None = {int(x) for x in admin_ids}
        else:
            self._local_admin_ids = None

    async def __call__(self, event: TelegramObject) -> bool:
        from_user: User | None = getattr(event, "from_user", None)
        if from_user is None:
            return False

        admin_ids = self._local_admin_ids if self._local_admin_ids is not None else TENANT_ADMIN_IDS
        return from_user.id in admin_ids
