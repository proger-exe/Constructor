from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from tgbot.database.managers import UserManager
from tgbot.keyboards.reply import admin_menu, main_menu

admin_router = Router(name="admin_panel")


@admin_router.message(Command(commands=["admin", "a"]))
async def admin_start_handler(message: Message):
    await message.reply(
        "👩‍💻 <b>Добро пожаловать, оператор 0 уровня.</b>", reply_markup=admin_menu()
    )


@admin_router.message(F.text == "📊 Cтатистика")
async def admin_stats_handler(message: Message):
    users = await UserManager.get_all()
    await message.reply(f"<b>Всего пользователей: {len(users)}</b> чел.")


@admin_router.message(F.text == "🔚 Назад")
async def admin_back_handler(message: Message):
    await message.reply("Добро пожаловать в Tenanter!", reply_markup=main_menu())
