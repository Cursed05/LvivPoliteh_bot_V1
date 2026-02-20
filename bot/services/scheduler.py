import time
import datetime
import asyncio
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from bot.database.queries import get_all_users
from bot.services.parser import fetch_schedule, invalidate_cache
from config import PAIR_TIMES, DAY_MAP_REVERSE

KYIV_TZ = pytz.timezone("Europe/Kyiv")

# Зберігаємо попередній розклад для детектора змін
_prev_schedules: dict = {}

# Для детекції сну системи (зсув часу)
_last_check_time: float = 0
_last_check_mono: float = 0


def format_lesson_notify(lesson: dict, subgroup: int = 0) -> str:
    """Форматує пару для сповіщення.
    subgroup: 0 = вся група, 1 = перша, 2 = друга.
    """
    lesson_type = lesson.get("type", "full")

    # Чисельник / знаменник
    if lesson_type == "num_den":
        num = lesson.get("numerator")
        den = lesson.get("denominator")
        active = None
        if num and num.get("is_active"):
            active = num
        elif den and den.get("is_active"):
            active = den
        else:
            parts = []
            if num:
                parts.append(f"📌 Чисельник: {num['info']}")
            if den:
                parts.append(f"📌 Знаменник: {den['info']}")
            return "\n".join(parts) if parts else "(невідома пара)"
        lines = [f"📖 {active['info']}"]
        if active.get("url"):
            lines.append(f"🔗 {active['url']}")
        return "\n".join(lines)

    # Підгрупи
    if lesson_type == "subgroups":
        sub1 = lesson.get("subgroup1")
        sub2 = lesson.get("subgroup2")
        # Вибираємо відповідну підгрупу
        if subgroup == 1:
            data = sub1
        elif subgroup == 2:
            data = sub2
        else:
            # Якщо підгрупа не вказана — показуємо обидві
            parts = []
            if sub1:
                parts.append(f"👥 1-ша підгрупа:\n📖 {sub1['info']}")
            if sub2:
                parts.append(f"👥 2-га підгрупа:\n📖 {sub2['info']}")
            return "\n\n".join(parts) if parts else "(невідома пара)"

        if not data:
            return "(невідома підгрупа)"
        lines = [f"📖 {data['info']}"]
        if data.get("url"):
            lines.append(f"🔗 {data['url']}")
        return "\n".join(lines)

    # Звичайна пара (full)
    info = lesson.get("info")
    if not info:
        return "(невідома пара)"
    lines = [f"📖 {info}"]
    if lesson.get("url"):
        lines.append(f"🔗 {lesson['url']}")
    return "\n".join(lines)


async def notify_before_class(bot: Bot):
    """Перевіряє кожну хвилину — чи є пара через N хвилин у кожного користувача."""
    global _last_check_time, _last_check_mono

    now = datetime.datetime.now(KYIV_TZ)
    current_time = now.timestamp()
    current_mono = time.monotonic()

    # Детекція "сну" системи/старого часу
    # Якщо з останньої перевірки пройшло мало часу за годинником, але багато за процесором —
    # значить система спала, а годинник ще не синхронізувався.
    if _last_check_time > 0:
        delta_wall = current_time - _last_check_time
        delta_mono = current_mono - _last_check_mono

        # Якщо різниця між монотонним часом і реальним > 60 сек
        # (наприклад, спали годину, а годинник каже пройшла 1 хв)
        if delta_mono - delta_wall > 60:
            print(f"[Warn] Clock drift detected! Sleep: {delta_mono:.1f}s, Wall: {delta_wall:.1f}s. Skipping...")
            _last_check_time = current_time
            _last_check_mono = current_mono
            return

    _last_check_time = current_time
    _last_check_mono = current_mono

    weekday = now.weekday()

    if weekday >= 6:  # Неділя
        return

    day_key = DAY_MAP_REVERSE.get(weekday)
    if not day_key:
        return

    users = await get_all_users()

    for user in users:
        if not user.get("notifications_on", 1):
            continue

        role = user.get("role", "student")
        semestr = user.get("semestr", 2)
        notify_before = user.get("notify_before", 15)

        # Отримуємо розклад залежно від ролі
        try:
            if role == "teacher":
                from bot.services.parser import fetch_teacher_schedule
                teacher_name = user.get("full_name", "").strip()
                if not teacher_name:
                    continue
                schedule = await fetch_teacher_schedule(teacher_name, semestr)
            else:
                group = user.get("group_name", "").strip()
                if not group:
                    continue
                schedule = await fetch_schedule(group, semestr)
        except Exception:
            continue

        lessons = schedule.get(day_key, [])
        user_subgroup = user.get("subgroup", 0)

        for lesson in lessons:
            pair_num = lesson.get("pair_num")
            if not pair_num:
                continue

            # Пропускаємо чужу підгрупу
            lesson_type = lesson.get("type", "full")
            if lesson_type == "subgroups" and user_subgroup in (1, 2):
                sub = lesson.get(f"subgroup{user_subgroup}")
                if not sub:
                    continue  # Ця підгрупа не має пари у цей час

            pair_time_str = PAIR_TIMES.get(pair_num)
            if not pair_time_str:
                continue

            pair_hour, pair_min = map(int, pair_time_str.split(":"))
            pair_dt = now.replace(hour=pair_hour, minute=pair_min, second=0, microsecond=0)
            diff = (pair_dt - now).total_seconds() / 60

            # Пара вже минула — пропускаємо
            if diff < 0:
                continue

            # Надсилаємо якщо залишилось рівно notify_before хвилин (±0.5 хв)
            if abs(diff - notify_before) <= 0.5:
                try:
                    formatted = format_lesson_notify(lesson, user_subgroup)
                    print(f"[DEBUG notify] uid={user['user_id']} subgroup={user_subgroup} type={lesson.get('type')} formatted={repr(formatted)}")
                    await bot.send_message(
                        user["user_id"],
                        f"⏰ <b>Через {notify_before} хвилин пара!</b>\n\n"
                        f"🕐 {lesson['pair']} ({pair_time_str})\n"
                        f"{formatted}",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"[DEBUG notify ERROR] {e}")


async def notify_evening(bot: Bot):
    """Щодня о 20:00 надсилає розклад на завтра."""
    tomorrow_num = (datetime.datetime.now(KYIV_TZ).weekday() + 1) % 7
    if tomorrow_num >= 6:
        return

    day_key = DAY_MAP_REVERSE.get(tomorrow_num)
    if not day_key:
        return

    day_names = {0: "Понеділок", 1: "Вівторок", 2: "Середа",
                 3: "Четвер", 4: "П'ятниця", 5: "Субота"}
    day_name = day_names.get(tomorrow_num, day_key)

    users = await get_all_users()

    for user in users:
        if not user.get("notify_evening"):
            continue

        group = user.get("group_name")
        semestr = user.get("semestr", 2)

        try:
            schedule = await fetch_schedule(group, semestr)
        except Exception:
            continue

        lessons = schedule.get(day_key, [])

        if not lessons:
            text = f"🌙 Завтра (<b>{day_name}</b>) пар немає. Відпочивай! 😊"
        else:
            from bot.handlers.schedule import format_lessons
            text = f"🌙 <b>Розклад на завтра — {day_name}</b>\n\n{format_lessons(lessons)}"

        try:
            await bot.send_message(user["user_id"], text, parse_mode="HTML")
        except Exception:
            pass


async def check_schedule_changes(bot: Bot):
    """Раз на годину перевіряє зміни в розкладі."""
    users = await get_all_users()
    checked = set()

    for user in users:
        group = user.get("group_name")
        semestr = user.get("semestr", 2)
        key = (group, semestr)

        if key in checked or not group:
            continue
        checked.add(key)

        try:
            # Інвалідуємо кеш щоб отримати свіжі дані
            invalidate_cache(group, semestr)
            new_schedule = await fetch_schedule(group, semestr)
        except Exception:
            continue

        old_schedule = _prev_schedules.get(key)

        if old_schedule is not None and old_schedule != new_schedule:
            # Знайшли зміни — сповіщаємо всіх з цією групою
            for u in users:
                if u.get("group_name") == group and u.get("semestr") == semestr:
                    try:
                        await bot.send_message(
                            u["user_id"],
                            "⚠️ <b>Розклад вашої групи змінився!</b>\n"
                            "Перевірте актуальний розклад: /week",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

        _prev_schedules[key] = new_schedule


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")

    # Кожну хвилину — перевірка сповіщень перед парою
    scheduler.add_job(notify_before_class, "interval", minutes=1, args=[bot])

    # Щодня о 20:00 — вечірнє нагадування
    scheduler.add_job(notify_evening, "cron", hour=20, minute=0, args=[bot])

    # Кожну годину — перевірка змін у розкладі
    scheduler.add_job(check_schedule_changes, "interval", hours=1, args=[bot])

    return scheduler
