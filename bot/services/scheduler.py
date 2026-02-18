import datetime
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from bot.database.queries import get_all_users
from bot.services.parser import fetch_schedule, invalidate_cache
from config import PAIR_TIMES, DAY_MAP_REVERSE

# Зберігаємо попередній розклад для детектора змін
_prev_schedules: dict = {}


def format_lesson_notify(lesson: dict) -> str:
    lines = [f"📖 {lesson['info']}"]
    if lesson.get("url"):
        lines.append(f"🔗 {lesson['url']}")
    return "\n".join(lines)


async def notify_before_class(bot: Bot):
    """Перевіряє кожну хвилину — чи є пара через N хвилин у кожного користувача."""
    now = datetime.datetime.now()
    weekday = now.weekday()

    if weekday >= 6:  # Неділя
        return

    day_key = DAY_MAP_REVERSE.get(weekday)
    if not day_key:
        return

    users = await get_all_users()

    for user in users:
        group = user.get("group_name")
        semestr = user.get("semestr", 2)
        notify_before = user.get("notify_before", 15)

        try:
            schedule = await fetch_schedule(group, semestr)
        except Exception:
            continue

        lessons = schedule.get(day_key, [])

        for lesson in lessons:
            pair_num = lesson.get("pair_num")
            if not pair_num:
                continue

            pair_time_str = PAIR_TIMES.get(pair_num)
            if not pair_time_str:
                continue

            pair_hour, pair_min = map(int, pair_time_str.split(":"))
            pair_dt = now.replace(hour=pair_hour, minute=pair_min, second=0, microsecond=0)
            diff = (pair_dt - now).total_seconds() / 60

            # Надсилаємо якщо залишилось рівно notify_before хвилин (±0.5 хв)
            if abs(diff - notify_before) <= 0.5:
                try:
                    await bot.send_message(
                        user["user_id"],
                        f"⏰ <b>Через {notify_before} хвилин пара!</b>\n\n"
                        f"🕐 {lesson['pair']} ({pair_time_str})\n"
                        f"{format_lesson_notify(lesson)}",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass


async def notify_evening(bot: Bot):
    """Щодня о 20:00 надсилає розклад на завтра."""
    tomorrow_num = (datetime.datetime.now().weekday() + 1) % 7
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
