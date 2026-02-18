import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
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


def format_lesson_block(info: str, url: str | None, label: str = "", is_active: bool = False) -> str:
    lines = []
    if label:
        lines.append(f"<i>{label}</i>")
    if is_active:
        # Активний тиждень — жирний текст
        lines.append(f"<b>{info}</b>")
    else:
        # Неактивний — звичайний текст
        lines.append(info)
    if url:
        lines.append(f"🔗 {url}")
    return "\n".join(lines)


def format_lessons(lessons: list) -> str:
    if not lessons:
        return "🎉 Пар немає!"
    lines = []
    for lesson in lessons:
        pair_num = lesson.get("pair_num")
        time_str = PAIR_TIMES_FULL.get(pair_num, "?")
        lines.append(f"🕐 <b>{lesson['pair']} пара  ({time_str})</b>")

        if lesson.get("numerator") or lesson.get("denominator"):
            num = lesson.get("numerator")
            den = lesson.get("denominator")
            if num:
                num_active = num.get("is_active", False)
                label = "✅ Чисельник (цей тиждень):" if num_active else "○ Чисельник (наст. тиждень):"
                lines.append(format_lesson_block(num["info"], num.get("url"), label, is_active=num_active))
            if den:
                den_active = den.get("is_active", False)
                label = "✅ Знаменник (цей тиждень):" if den_active else "○ Знаменник (наст. тиждень):"
                lines.append(format_lesson_block(den["info"], den.get("url"), label, is_active=den_active))
        else:
            lines.append(lesson["info"])
            if lesson.get("url"):
                lines.append(f"🔗 {lesson['url']}")

        lines.append("")
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

    await message.answer(
        f"📅 <b>{day_name}</b> | {label}\n\n{format_lessons(lessons)}",
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

    await message.answer(
        f"➡️ <b>{day_name}</b> | {label}\n\n{format_lessons(lessons)}",
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

    day_order = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    await message.answer(f"📆 <b>Розклад на тиждень</b> | {label}", parse_mode="HTML")

    for day_key in day_order:
        if day_key not in schedule:
            continue
        lessons = schedule[day_key]
        day_num = DAY_MAP.get(day_key, 0)
        day_name = DAY_NAMES_UA.get(day_num, day_key)
        text = f"📌 <b>{day_name}</b>\n\n{format_lessons(lessons)}"
        await message.answer(text, parse_mode="HTML")
