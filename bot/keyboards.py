from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Сьогодні"), KeyboardButton(text="➡️ Завтра")],
        [KeyboardButton(text="📆 Тиждень")],
        [KeyboardButton(text="👨‍🏫 Розклад викладача"), KeyboardButton(text="📝 Екзамени")],
        [KeyboardButton(text="⚙️ Налаштування")],
        [KeyboardButton(text="💬 Зв'язатись з розробником")],
    ],
    resize_keyboard=True,
)

DEVELOPER_KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💬 Написати розробнику", url="https://t.me/D34dEndR1der_2005")]
])
