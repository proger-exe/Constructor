from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from tgbot.keyboards.tenant.inline import main_keyboard

user_tenant_router = Router(name="user_router")

answ = {
    "first-button": ("answ", None),
    "second-button": ("answ", None),
    "third-button": ("answ", None),
    "four-button": ("answ", None),
}


@user_tenant_router.message(CommandStart())
async def tenant_start_handler(message: Message, bot: Bot):
    await message.reply("Привет!", reply_markup=main_keyboard())


@user_tenant_router.callback_query(F.data.in_(answ))
async def answer_user(call: CallbackQuery):
    button = answ.get(call.data)
    text, keyboard = button

    await call.message.answer(
        text,
        reply_markup=keyboard,
    )
