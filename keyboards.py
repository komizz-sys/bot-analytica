from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Сегодня"), KeyboardButton(text="📅 Неделя")],
            [KeyboardButton(text="🗓 Месяц"), KeyboardButton(text="♾ За всё время")],
            [KeyboardButton(text="💸 Добавить расход"), KeyboardButton(text="📃 История расходов")],
        ],
        resize_keyboard=True,
    )
