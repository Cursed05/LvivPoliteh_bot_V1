import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.queries import get_user
from bot.services.parser import fetch_schedule, fetch_teacher_schedule
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import DAY_MAP, DAY_MAP_REVERSE, PAIR_TIMES, PAIR_TIMES_FULL

router = Router()

DAY_NAMES_UA = {
    0: "Понеділок", 1: "Вівторок", 2: "Середа",
    3: "Четвер", 4: "П'ятниця", 5: "Субота", 6: "Неділя"
}

DAY_ORDER = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
DAY_FULL_NAMES = {
    "Пн": "Понеділок", "Вт": "Вівторок", "Ср": "Середа",
    "Чт": "Четвер", "Пт": "П'ятниця", "Сб": "Субота"
}


def week_keyboard(active_day: str, available_days: list[str]) -> InlineKeyboardMarkup:
    """Inline кнопки днів тижня. Активний день позначений ●."""
    buttons = []
    for day in DAY_ORDER:
        if day not in available_days:
            continue
        label = f"● {day}" if day == active_day else day
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"week_day:{day}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])



def format_lesson_block(info: str, url: str | None, label: str = "", is_active: bool = False) -> str:
    lines = []
    if label:
        lines.append(f"<i>{label}</i>")
    if is_active:
        lines.append(f"<b>{info}</b>")
    else:
        lines.append(info)
    if url:
        lines.append(f"🔗 {url}")
    return "\n".join(lines)


def format_lessons(lessons: list, subgroup: int = 0) -> str:
    if not lessons:
        return "🎉 Пар немає!"
    lines = []
    shown = 0
    for lesson in lessons:
        pair_num = lesson.get("pair_num")
        time_str = PAIR_TIMES_FULL.get(pair_num, "?")
        lesson_type = lesson.get("type", "full")

        if lesson_type == "subgroups":
            sub1 = lesson.get("subgroup1")
            sub2 = lesson.get("subgroup2")
            # Фільтр підгрупи
            show_sub1 = sub1 and subgroup in (0, 1)
            show_sub2 = sub2 and subgroup in (0, 2)
            if not show_sub1 and not show_sub2:
                continue
            shown += 1
            lines.append(f"🕐 <b>{lesson['pair']} пара  ({time_str})</b>")
            if show_sub1:
                lines.append(format_lesson_block(sub1["info"], sub1.get("url"), "👥 1-ша підгрупа:"))
            if show_sub2:
                lines.append(format_lesson_block(sub2["info"], sub2.get("url"), "👥 2-га підгрупа:"))

        elif lesson_type == "num_den":
            num = lesson.get("numerator")
            den = lesson.get("denominator")
            if not num and not den:
                continue
            shown += 1
            lines.append(f"🕐 <b>{lesson['pair']} пара  ({time_str})</b>")
            if num:
                num_active = num.get("is_active", False)
                label = "✅ Чисельник (цей тиждень):" if num_active else "○ Чисельник (наст. тиждень):"
                lines.append(format_lesson_block(num["info"], num.get("url"), label, is_active=num_active))
            if den:
                den_active = den.get("is_active", False)
                label = "✅ Знаменник (цей тиждень):" if den_active else "○ Знаменник (наст. тиждень):"
                lines.append(format_lesson_block(den["info"], den.get("url"), label, is_active=den_active))

        else:
            # Звичайна пара для всієї групи
            shown += 1
            lines.append(f"🕐 <b>{lesson['pair']} пара  ({time_str})</b>")
            lines.append(lesson.get("info", ""))
            if lesson.get("url"):
                lines.append(f"🔗 {lesson['url']}")

        lines.append("")

    if shown == 0:
        return "🎉 Пар немає!"
    return "\n".join(lines).strip()


async def get_schedule_for_user(user: dict) -> tuple[dict, str]:
    """Повертає (розклад, заголовок) залежно від ролі."""
    role = user.get("role", "student")
    semestr = user.get("semestr", 2)

    if role == "teacher":
        full_name = user.get("full_name", "").strip()
        if not full_name:
            return {}, None
        schedule = await fetch_teacher_schedule(full_name, semestr)
        return schedule, full_name
    else:
        group = user.get("group_name", "").strip()
        if not group:
            return {}, None
        schedule = await fetch_schedule(group, semestr)
        return schedule, group


async def check_user_setup(message: Message) -> dict | None:
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("⚠️ Спочатку налаштуйте профіль в <b>⚙️ Налаштуваннях</b>!", parse_mode="HTML")
        return None

    role = user.get("role", "student")
    if role == "teacher" and not user.get("full_name"):
        await message.answer(
            "⚠️ Для викладача необхідно вказати <b>ПІБ повністю</b> в особистому кабінеті!\n"
            "Відкрийте ⚙️ Налаштування → 👤 Особистий кабінет → ✏️ Змінити ПІБ",
            parse_mode="HTML"
        )
        return None
    if role == "student" and not user.get("group_name"):
        await message.answer(
            "⚠️ Вкажіть свою групу в <b>⚙️ Налаштуваннях</b>!",
            parse_mode="HTML"
        )
        return None
    return user


def build_day_text(day_key: str, lessons: list, label: str, subgroup: int) -> str:
    """Формує текст для одного дня."""
    day_name = DAY_FULL_NAMES.get(day_key, day_key)
    subgroup_labels = {0: "", 1: " · 1-ша підгрупа", 2: " · 2-га підгрупа"}
    sg_suffix = subgroup_labels.get(subgroup, "")
    header = f"📆 <b>{day_name}</b> | {label}{sg_suffix}"
    return f"{header}\n\n{format_lessons(lessons, subgroup)}"


@router.message(F.text == "📅 Сьогодні")
@router.message(Command("today"))
async def cmd_today(message: Message):
    user = await check_user_setup(message)
    if not user:
        return

    today_num = datetime.datetime.now().weekday()
    today_key = DAY_MAP_REVERSE.get(today_num)

    if today_num >= 6:
        await message.answer("😴 Сьогодні неділя — пар немає!")
        return

    schedule, label = await get_schedule_for_user(user)
    lessons = schedule.get(today_key, [])
    day_name = DAY_NAMES_UA.get(today_num, today_key)
    subgroup = user.get("subgroup", 0)

    await message.answer(
        f"📅 <b>{day_name}</b> | {label}\n\n{format_lessons(lessons, subgroup)}",
        parse_mode="HTML"
    )


@router.message(F.text == "➡️ Завтра")
@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message):
    user = await check_user_setup(message)
    if not user:
        return

    tomorrow_num = (datetime.datetime.now().weekday() + 1) % 7
    tomorrow_key = DAY_MAP_REVERSE.get(tomorrow_num)

    if tomorrow_num >= 6:
        await message.answer("😴 Завтра неділя — пар немає!")
        return

    schedule, label = await get_schedule_for_user(user)
    lessons = schedule.get(tomorrow_key, [])
    day_name = DAY_NAMES_UA.get(tomorrow_num, tomorrow_key)
    subgroup = user.get("subgroup", 0)

    await message.answer(
        f"➡️ <b>{day_name}</b> | {label}\n\n{format_lessons(lessons, subgroup)}",
        parse_mode="HTML"
    )


@router.message(F.text == "📆 Тиждень")
@router.message(Command("week"))
async def cmd_week(message: Message):
    user = await check_user_setup(message)
    if not user:
        return

    schedule, label = await get_schedule_for_user(user)

    if not schedule:
        await message.answer("❌ Розклад не знайдено. Перевірте налаштування профілю.")
        return

    subgroup = user.get("subgroup", 0)
    available_days = [d for d in DAY_ORDER if d in schedule]

    # Починаємо з поточного дня або понеділка
    today_num = datetime.datetime.now().weekday()
    today_key = DAY_MAP_REVERSE.get(today_num)
    start_day = today_key if today_key in available_days else (available_days[0] if available_days else "Пн")

    lessons = schedule.get(start_day, [])
    text = build_day_text(start_day, lessons, label, subgroup)

    # Зберігаємо розклад у callback_data через user_id (кешується в parser)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=week_keyboard(start_day, available_days)
    )


@router.callback_query(F.data.startswith("week_day:"))
async def cb_week_day(callback: CallbackQuery):
    day_key = callback.data.split(":")[1]

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("⚠️ Профіль не налаштований")
        return

    schedule, label = await get_schedule_for_user(user)
    subgroup = user.get("subgroup", 0)
    available_days = [d for d in DAY_ORDER if d in schedule]
    lessons = schedule.get(day_key, [])
    text = build_day_text(day_key, lessons, label, subgroup)

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=week_keyboard(day_key, available_days)
        )
    except Exception:
        pass  # Текст не змінився
    await callback.answer()
