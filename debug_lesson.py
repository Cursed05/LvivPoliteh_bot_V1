import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot.services.parser import fetch_schedule

async def main():
    # Замінити на реальну групу
    group = input("Введи групу (наприклад так в ): ").strip()
    semestr = 2
    schedule = await fetch_schedule(group, semestr)

    # Сьогоднішній день
    import datetime
    import pytz

    KYIV_TZ = pytz.timezone("Europe/Kyiv")
    now = datetime.datetime.now(KYIV_TZ)
    # Словник для дня тижня
    day_map = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Нд"}
    day_key = day_map.get(now.weekday())

    lessons = schedule.get(day_key, [])
    print(f"\nДень: {day_key}, пар: {len(lessons)}")
    print("-" * 50)

    for lesson in lessons:
        print(f"Пара: {lesson.get('pair')}")
        print(f"  type:      {lesson.get('type')}")
        print(f"  info:      {lesson.get('info')}")
        print(f"  subgroup1: {lesson.get('subgroup1')}")
        print(f"  subgroup2: {lesson.get('subgroup2')}")
        print(f"  numerator: {lesson.get('numerator')}")
        print(f"  denominator: {lesson.get('denominator')}")
        print()

asyncio.run(main())
