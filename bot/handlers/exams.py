import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from bot.database.queries import get_user
from bot.services.parser import fetch_exam_schedule, fetch_teacher_exam_schedule
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import PAIR_TIMES_FULL

router = Router()

UA_MONTHS = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня",
}

UA_WEEKDAYS = {
    0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Нд"
}


def format_date(date_str: str) -> str:
    """2026-01-06 → 6 січня (Вт)"""
    try:
        d = datetime.date.fromisoformat(date_str)
        weekday = UA_WEEKDAYS.get(d.weekday(), "")
        month = UA_MONTHS.get(d.month, "")
        return f"{d.day} {month} ({weekday})"
    except Exception:
        return date_str


def format_exams(exams: list, today: datetime.date) -> str:
    lines = []
    for exam in exams:
        date_str = exam["date"]
        pair_num = exam.get("pair_num")
        time_str = PAIR_TIMES_FULL.get(pair_num, "?")
        date_label = format_date(date_str)

        try:
            exam_date = datetime.date.fromisoformat(date_str)
            past = exam_date < today
        except Exception:
            past = False

        prefix = "✅" if past else "📌"
        lines.append(f"{prefix} <b>{date_label}</b>  |  {exam['pair']} пара ({time_str})")
        lines.append(exam["info"])
        lines.append("")
    return "\n".join(lines).strip()


@router.message(F.text == "📝 Екзамени")
@router.message(Command("exams"))
async def cmd_exams(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("⚠️ Спочатку налаштуйте профіль в <b>⚙️ Налаштуваннях</b>!", parse_mode="HTML")
        return

    role = user.get("role", "student")
    today = datetime.date.today()

    if role == "teacher":
        full_name = user.get("full_name", "").strip()
        if not full_name:
            await message.answer(
                "⚠️ Для викладача необхідно вказати <b>ПІБ повністю</b> в особистому кабінеті!\n"
                "Відкрийте ⚙️ Налаштування → 👤 Особистий кабінет → ✏️ Змінити ПІБ",
                parse_mode="HTML"
            )
            return

        await message.answer(f"⏳ Завантажую розклад екзаменів для <b>{full_name}</b>...", parse_mode="HTML")
        try:
            exams = await fetch_teacher_exam_schedule(full_name)
        except Exception:
            await message.answer("❌ Помилка при отриманні розкладу екзаменів. Спробуйте пізніше.")
            return

        if not exams:
            await message.answer(
                f"📝 Розклад екзаменів для <b>{full_name}</b> не знайдено.",
                parse_mode="HTML"
            )
            return

        header = f"📝 <b>Розклад екзаменів</b>\n👨‍🏫 {full_name}\n"
        await message.answer(header + "\n" + format_exams(exams, today), parse_mode="HTML")

    else:
        group = user.get("group_name", "").strip()
        if not group:
            await message.answer(
                "⚠️ Вкажіть свою групу в <b>⚙️ Налаштуваннях</b>!",
                parse_mode="HTML"
            )
            return

        await message.answer(f"⏳ Завантажую розклад екзаменів для <b>{group}</b>...", parse_mode="HTML")
        try:
            exams = await fetch_exam_schedule(group)
        except Exception:
            await message.answer("❌ Помилка при отриманні розкладу екзаменів. Спробуйте пізніше.")
            return

        if not exams:
            await message.answer(
                f"📝 Розклад екзаменів для <b>{group}</b> не знайдено.\n"
                "Можливо, екзамени ще не заплановані або група вказана невірно.",
                parse_mode="HTML"
            )
            return

        header = f"📝 <b>Розклад екзаменів</b> | {group}\n"
        await message.answer(header + "\n" + format_exams(exams, today), parse_mode="HTML")
