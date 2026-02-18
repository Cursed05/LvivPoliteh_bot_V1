from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Сьогодні"), KeyboardButton(text="➡️ Завтра")],
        [KeyboardButton(text="📆 Тиждень")],
        [KeyboardButton(text="👨‍🏫 Розклад викладача"), KeyboardButton(text="📝 Екзамени")],
        [KeyboardButton(text="⚙️ Налаштування")],
    ],
    resize_keyboard=True,
)
