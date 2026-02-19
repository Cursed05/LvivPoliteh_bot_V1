import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from bot.database.db import init_db
from bot.handlers import start, settings, schedule
from bot.handlers import teacher_lookup
from bot.handlers import exams
from bot.handlers import admin
from bot.services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # Ініціалізація бази даних
    await init_db()
    logger.info("Database initialized")

    # Бот та диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Реєстрація handlers
    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(schedule.router)
    dp.include_router(teacher_lookup.router)
    dp.include_router(exams.router)
    dp.include_router(admin.router)

    # Запуск планувальника
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler started")

    logger.info("Bot started polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
