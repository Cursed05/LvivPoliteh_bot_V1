import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "bot_data.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id          INTEGER PRIMARY KEY,
                role             TEXT DEFAULT 'student',
                full_name        TEXT,
                group_name       TEXT,
                subgroup         INTEGER DEFAULT 0,
                semestr          INTEGER DEFAULT 2,
                notify_before    INTEGER DEFAULT 15,
                notify_evening   BOOLEAN DEFAULT 1,
                notifications_on BOOLEAN DEFAULT 1
            )
        """)
        # Міграція: додаємо нові колонки якщо їх немає (для існуючих БД)
        for col, definition in [
            ("role", "TEXT DEFAULT 'student'"),
            ("full_name", "TEXT"),
            ("subgroup", "INTEGER DEFAULT 0"),
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except Exception:
                pass  # Колонка вже існує
        await db.commit()
