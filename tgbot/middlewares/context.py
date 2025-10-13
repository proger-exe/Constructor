from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware

from tgbot.common.logging_setup import user_id_var


class ContextLoggingMiddleware(BaseMiddleware):
    """
    Propagate tenant_id (from context var set by request handler) and user_id
    (from incoming update) to logging context used by your JSON logger.
    """

    async def __call__(
        self,
        handler: Callable[[Dict[str, Any], Any], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        update = data.get("event_update") or data.get("update")
        uid = None
        if update:
            if update.message:
                uid = update.message.from_user.id
            elif update.edited_message:
                uid = update.edited_message.from_user.id
            elif update.callback_query:
                uid = update.callback_query.from_user.id
        if uid is not None:
            user_id_var.set(uid)

        return await handler(event, data)
