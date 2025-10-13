from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

admin_router = Router(name="tenant_admin")


@admin_router.message(Command("admin"))
async def admin_handler(msg: Message):
    await msg.answer("💎")
    await msg.answer("Welcome, admin!")


@admin_router.message(F.text == "")