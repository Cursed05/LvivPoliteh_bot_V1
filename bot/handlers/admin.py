from aiogram import Router, types, F
from aiogram.filters import Command
from config import ADMIN_IDS
from bot.database.queries import get_users_for_broadcast
import asyncio

router = Router()

@router.message(Command("message"))
async def broadcast_message(message: types.Message):
    # 1. Перевірка на адміна
    if message.from_user.id not in ADMIN_IDS:
        return

    # 2. Отримуємо параметри для розсилки
    text_to_send = None
    photo_id = None
    
    # Визначаємо аргументи команди (все що після /message)
    command_args = ""
    if message.text:
        command_args = message.text.replace("/message", "", 1).strip()
    elif message.caption:
        command_args = message.caption.replace("/message", "", 1).strip()
        
    # Сценарій А: Команда з прикріпленим фото
    if message.photo:
        photo_id = message.photo[-1].file_id
        text_to_send = command_args
        
    # Сценарій Б: Реплай на повідомлення
    elif message.reply_to_message:
        reply = message.reply_to_message
        
        # Якщо реплай на фото
        if reply.photo:
            photo_id = reply.photo[-1].file_id
            # Якщо адмін написав текст в команді - беремо його, інакше підпис фото
            text_to_send = command_args if command_args else (reply.caption or "")
            
        # Якщо реплай на текст
        elif reply.text:
             # Якщо адмін написав текст в команді - беремо його, інакше текст повідомлення
            text_to_send = command_args if command_args else reply.text

    # Сценарій В: Просто текст
    else:
        text_to_send = command_args

    # Валідація: чи є що відправляти
    if not text_to_send and not photo_id:
        await message.answer(
            "⚠️ <b>Помилка!</b>\n"
            "Введіть текст або прикріпіть фото.\n"
            "Приклад: <code>/message Оновлення бота!</code>", 
            parse_mode="HTML"
        )
        return

    # 3. Отримуємо користувачів
    users = await get_users_for_broadcast()
    total = len(users)
    sent_count = 0
    error_count = 0
    
    status_msg = await message.answer(f"📢 Починаю розсилку для {total} користувачів...")
    
    # 4. Розсилаємо
    for user_id in users:
        try:
            if photo_id:
                await message.bot.send_photo(chat_id=user_id, photo=photo_id, caption=text_to_send, parse_mode="HTML")
            else:
                await message.bot.send_message(chat_id=user_id, text=text_to_send, parse_mode="HTML")
            
            sent_count += 1
            # Невелика затримка щоб не ловити FloodWait при великій кількості
            await asyncio.sleep(0.05) 
            
        except Exception:
            error_count += 1
            
    await status_msg.edit_text(
        f"✅ <b>Розсилку завершено!</b>\n"
        f"👥 Всього: {total}\n"
        f"📨 Надіслано: {sent_count}\n"
        f"❌ Помилки (блокували): {error_count}",
        parse_mode="HTML"
    )
