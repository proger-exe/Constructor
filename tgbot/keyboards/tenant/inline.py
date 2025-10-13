from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_keyboard():
    markup = InlineKeyboardBuilder()

    markup.add(
        InlineKeyboardButton(
            text="", 
            callback_data=""
        ),
        InlineKeyboardButton(text="", callback_data=""),
        InlineKeyboardButton(text="", callback_data=""),
        InlineKeyboardButton(text="", callback_data=""),
    )
    markup.adjust(1, repeat=True)
    return markup.as_markup()


