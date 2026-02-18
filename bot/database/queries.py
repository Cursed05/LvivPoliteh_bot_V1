import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "bot_data.db")


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def upsert_user(user_id: int, **kwargs):
    """Створює або оновлює запис користувача."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Перевіряємо чи існує
        async with db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            exists = await cursor.fetchone()

        if not exists:
            await db.execute(
                "INSERT INTO users (user_id) VALUES (?)", (user_id,)
            )

        if kwargs:
            sets = ", ".join(f"{k} = ?" for k in kwargs)
            values = list(kwargs.values()) + [user_id]
            await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", values)

        await db.commit()


async def get_all_users() -> list[dict]:
    """Повертає всіх користувачів з увімкненими сповіщеннями та вказаною групою."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE notifications_on = 1 AND group_name IS NOT NULL"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
