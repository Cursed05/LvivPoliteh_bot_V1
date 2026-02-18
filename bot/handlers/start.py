from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from bot.keyboards import MAIN_MENU

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привіт! Я бот розкладу <b>Львівської Політехніки</b>.\n\n"
        "Щоб почати — натисни <b>⚙️ Налаштування</b> і вкажи свою групу.",
        parse_mode="HTML",
        reply_markup=MAIN_MENU,
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 <b>Команди бота:</b>\n\n"
        "/start — головне меню\n"
        "/help — ця довідка\n\n"
        "📅 <b>Сьогодні</b> — розклад на сьогодні\n"
        "➡️ <b>Завтра</b> — розклад на завтра\n"
        "📆 <b>Тиждень</b> — повний розклад\n"
        "⚙️ <b>Налаштування</b> — група, семестр, сповіщення",
        parse_mode="HTML",
    )
