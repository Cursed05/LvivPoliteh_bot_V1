from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database.queries import get_user
from bot.services.parser import fetch_teacher_schedule
from bot.handlers.schedule import format_lessons
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import DAY_MAP, DAY_MAP_REVERSE

router = Router()

DAY_NAMES_UA = {
    0: "Понеділок", 1: "Вівторок", 2: "Середа",
    3: "Четвер", 4: "П'ятниця", 5: "Субота", 6: "Неділя"
}

CANCEL_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Скасувати")]],
    resize_keyboard=True,
)


class TeacherLookupStates(StatesGroup):
    waiting_teacher_name = State()
    waiting_semestr = State()


@router.message(F.text == "👨‍🏫 Розклад викладача")
async def cmd_teacher_lookup(message: Message, state: FSMContext):
    await message.answer(
        "🔍 Введіть <b>ПІБ викладача повністю</b>\n"
        "(наприклад: <b>Банах Василь Михайлович</b>)\n\n"
        "Натисніть ❌ Скасувати щоб повернутись до меню.",
        parse_mode="HTML",
        reply_markup=CANCEL_KB,
    )
    await state.set_state(TeacherLookupStates.waiting_teacher_name)


@router.message(TeacherLookupStates.waiting_teacher_name, F.text == "❌ Скасувати")
async def cancel_teacher_lookup(message: Message, state: FSMContext):
    from bot.keyboards import MAIN_MENU
    await state.clear()
    await message.answer("🏠 Головне меню", reply_markup=MAIN_MENU)


@router.message(TeacherLookupStates.waiting_teacher_name)
async def process_teacher_name(message: Message, state: FSMContext):
    teacher_name = message.text.strip()
    await state.update_data(teacher_name=teacher_name)

    # Отримуємо семестр з профілю користувача (або питаємо)
    user = await get_user(message.from_user.id)
    semestr = user.get("semestr", 2) if user else 2

    await state.clear()
    await message.answer(f"⏳ Шукаю розклад для <b>{teacher_name}</b>...", parse_mode="HTML")

    try:
        schedule = await fetch_teacher_schedule(teacher_name, semestr)
    except Exception as e:
        from bot.keyboards import MAIN_MENU
        await message.answer("❌ Помилка при отриманні розкладу. Спробуйте пізніше.", reply_markup=MAIN_MENU)
        return

    from bot.keyboards import MAIN_MENU

    if not schedule:
        await message.answer(
            f"❌ Розклад для <b>{teacher_name}</b> не знайдено.\n"
            "Перевірте правильність написання ПІБ (повністю, як на сайті ЛП).",
            parse_mode="HTML",
            reply_markup=MAIN_MENU,
        )
        return

    day_order = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    sem_label = "весняний" if semestr == 2 else "осінній"
    await message.answer(
        f"📆 <b>Розклад викладача</b>\n👨‍🏫 {teacher_name}\n📚 {sem_label} семестр",
        parse_mode="HTML",
        reply_markup=MAIN_MENU,
    )

    found_any = False
    for day_key in day_order:
        if day_key not in schedule:
            continue
        lessons = schedule[day_key]
        day_num = DAY_MAP.get(day_key, 0)
        day_name = DAY_NAMES_UA.get(day_num, day_key)
        text = f"📌 <b>{day_name}</b>\n\n{format_lessons(lessons)}"
        await message.answer(text, parse_mode="HTML")
        found_any = True

    if not found_any:
        await message.answer(
            f"🎉 У <b>{teacher_name}</b> пар немає або розклад порожній.",
            parse_mode="HTML"
        )
