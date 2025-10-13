from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton as ib
from aiogram.types import InlineKeyboardMarkup, Message

from tgbot.bootstrap import load_settings
from tgbot.database.managers import TenantManager, UserManager
from tgbot.keyboards.reply import main_menu, menu_kb
from tgbot.misc.utils import is_bot_token
from tgbot.services.tenants import TenantContext

user_router = Router(name="user_router")

REPLICA_WEBHOOK_PATH = "/webhook/{tenant_uid}"


_app_settings = None
_vault = None
_tenant_service = None


def bootstrap_once():
    global _app_settings, _vault, _tenant_service
    if _app_settings is None:
        _app_settings, _, _vault, _tenant_service = load_settings()
    return _app_settings, _vault, _tenant_service


async def get_webhook_secret():
    _, vault, _ = bootstrap_once()
    secret = vault.read_kv("tgbot/common/webhook_secret")
    return secret.get("webhook_secret")


@user_router.message(CommandStart())
async def user_start_handler(message: Message):
    await UserManager(message.from_user.id).create()
    await message.reply("Добро пожаловать в бот!", reply_markup=main_menu())


@user_router.message(F.text == "Главное меню")
async def main_menu_handler(message: Message):
    await message.reply("Вы перешли в главное меню.", reply_markup=menu_kb())


@user_router.message(F.text == "Добавить бота")
async def add_bot_handler(message: Message, state: FSMContext):
    await state.set_state("add_bot")
    await message.reply("Отправьте токен бота: ")


@user_router.message(StateFilter("add_bot"), F.text.func(is_bot_token))
async def add_bot_payload(message: Message, state: FSMContext, bot: Bot):
    app_settings, vault, tenant_service = bootstrap_once()
    webhook_secret = await get_webhook_secret()

    new_bot = Bot(token=message.text, session=bot.session)
    try:
        bot_user = await new_bot.get_me()
    except TelegramUnauthorizedError:
        await state.clear()
        return await message.answer("Неверный токен.")

    tenant_uid = str(uuid4())
    created = await TenantManager(message.from_user.id).create(uid=tenant_uid)
    if created is None:
        await state.clear()
        return await message.reply("Этот токен уже есть в нашей базе.")

    vault.write_kv(f"tgbot/tenants/{tenant_uid}", {"bot_token": message.text})

    tenant_service.put_context(
        TenantContext(tenant_uid=tenant_uid, bot_token=message.text, version=1)
    )

    await new_bot.delete_webhook(drop_pending_updates=True)
    await new_bot.set_webhook(
        url=app_settings.external_base_url.rstrip("/")
        + REPLICA_WEBHOOK_PATH.format(tenant_uid=tenant_uid),
        secret_token=webhook_secret,
    )
    await new_bot.session.close()

    await state.clear()
    return await message.answer(f"Бот @{bot_user.username} был успешно добавлен!")


@user_router.message(F.text == "Мои боты")
async def my_bots_menu(message: Message):
    _, vault, tenant_service = bootstrap_once()
    tenants = await TenantManager(message.from_user.id).get_all()
    tenant_uids = [t.uuid for t in tenants]

    # Bulk-load contexts (cache first, Vault for misses, limited concurrency)
    ctx_map = await tenant_service.get_contexts(tenant_uids)

    kb = []
    for t in tenants:
        ctx = ctx_map.get(t.uuid)
        if not ctx:
            # If something went wrong for a specific tenant, just skip it
            continue
        new_bot = Bot(token=ctx.bot_token)
        try:
            bot_user = await new_bot.get_me()
            kb.append(
                [ib(text=f"@{bot_user.username}", callback_data=f"manage_bot:{t.uuid}")]
            )
        except TelegramUnauthorizedError:
            vault.delete_kv(f"tgbot/tenants/{t.uuid}")
            tenant_service.invalidate(t.uuid)
            await TenantManager.delete(t.uuid)

        finally:
            await new_bot.session.close()

    markup = InlineKeyboardMarkup(row_width=1, inline_keyboard=kb)
    await message.reply(
        "Выберите бота:" if kb else "У вас нет ботов.",
        reply_markup=markup if kb else None,
    )


@user_router.callback_query(F.data.startswith("manage_bot"))
async def manage_bot_menu(call: CallbackQuery):
    _, _, tenant_service = bootstrap_once()
    tenant_uid = call.data.split(":")[1]
    ctx = await tenant_service.get_context(tenant_uid)

    new_bot = Bot(token=ctx.bot_token)
    try:
        bot_user = await new_bot.get_me()
        txt = f"<b>Информация о боте: @{bot_user.username}</b>\n\nСтатус: 🟢 Работает"
    except TelegramUnauthorizedError:
        txt = "У этого бота не работает токен."
    finally:
        await new_bot.session.close()

    kb = [
        [ib(text="⚠️ Удалить бота", callback_data=f"delete_bot:{tenant_uid}")],
        [ib(text="Назад", callback_data="back2bots")],
    ]
    markup = InlineKeyboardMarkup(row_width=1, inline_keyboard=kb)
    await call.message.edit_text(txt, reply_markup=markup)


@user_router.callback_query(F.data.startswith("delete_bot"))
async def delete_bot_payload(call: CallbackQuery):
    _, vault, tenant_service = bootstrap_once()
    tenant_uid = call.data.split(":")[1]
    ctx = await tenant_service.get_context(tenant_uid)

    bot = Bot(token=ctx.bot_token)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

    vault.delete_kv(f"tgbot/tenants/{tenant_uid}")

    tenant_service.invalidate(tenant_uid)

    await TenantManager.delete(tenant_uid)

    markup = InlineKeyboardMarkup(
        row_width=1, inline_keyboard=[[ib(text="Назад", callback_data="back2bots")]]
    )
    await call.message.edit_text("Бот был успешно удалён!", reply_markup=markup)


@user_router.callback_query(F.data == "back2bots")
async def manage_bot_back(call: CallbackQuery):
    return await my_bots_menu(call.message)
