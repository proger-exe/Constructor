"Reply keyboard management module."

from aiogram.types import KeyboardButton as rb
from aiogram.types import ReplyKeyboardMarkup


def main_menu():
    kb = [
        [rb(text="Главное меню")],
    ]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    return markup


def menu_kb():
    kb = [
        [rb(text="Добавить бота"), rb(text="Мои боты")],
    ]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    return markup


def admin_menu():
    kb = [[rb(text="📊 Cтатистика")], [rb(text="🔚 Назад")]]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    return markup
