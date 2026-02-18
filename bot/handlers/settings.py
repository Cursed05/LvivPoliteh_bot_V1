from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database.queries import get_user, upsert_user

router = Router()


class SettingsStates(StatesGroup):
    # Особистий кабінет
    waiting_full_name = State()
    waiting_group = State()
    # Сповіщення
    waiting_notify_before = State()


# ─── Клавіатури ────────────────────────────────────────────────────────────────

def main_settings_keyboard(user: dict) -> InlineKeyboardMarkup:
    role = user.get("role", "student")
    role_label = "👨‍🎓 Студент" if role == "student" else "👨‍🏫 Викладач"
    full_name = user.get("full_name") or "не вказано"
    group = user.get("group_name") or "не вказана"
    sem = user.get("semestr", 2)
    notif_status = "✅" if user.get("notifications_on") else "❌"
    evening_status = "✅" if user.get("notify_evening") else "❌"
    before = user.get("notify_before", 15)

    rows = [
        [InlineKeyboardButton(text="👤 Особистий кабінет", callback_data="open_cabinet")],
        [InlineKeyboardButton(text=f"📚 Семестр: {sem}", callback_data="set_semestr")],
    ]
    if role == "student":
        rows.insert(1, [InlineKeyboardButton(text=f"🏫 Група: {group}", callback_data="set_group")])

    rows += [
        [InlineKeyboardButton(text=f"⏰ Сповіщення за: {before} хв", callback_data="set_notify_before")],
        [InlineKeyboardButton(text=f"🌙 Вечірнє нагадування: {evening_status}", callback_data="toggle_evening")],
        [InlineKeyboardButton(text=f"🔔 Сповіщення: {notif_status}", callback_data="toggle_notifications")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cabinet_keyboard(user: dict) -> InlineKeyboardMarkup:
    role = user.get("role", "student")
    role_label = "👨‍🎓 Студент" if role == "student" else "👨‍🏫 Викладач"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎭 Роль: {role_label}", callback_data="set_role")],
        [InlineKeyboardButton(text="✏️ Змінити ПІБ", callback_data="set_full_name")],
        [InlineKeyboardButton(text="◀️ Назад до налаштувань", callback_data="back_to_settings")],
    ])


def role_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨‍🎓 Студент", callback_data="role_student"),
            InlineKeyboardButton(text="👨‍🏫 Викладач", callback_data="role_teacher"),
        ]
    ])


def semestr_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ Перший", callback_data="semestr_1"),
            InlineKeyboardButton(text="2️⃣ Другий", callback_data="semestr_2"),
        ]
    ])


def notify_before_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10 хв", callback_data="before_10"),
            InlineKeyboardButton(text="15 хв", callback_data="before_15"),
            InlineKeyboardButton(text="20 хв", callback_data="before_20"),
            InlineKeyboardButton(text="30 хв", callback_data="before_30"),
        ]
    ])


# ─── Тексти ────────────────────────────────────────────────────────────────────

def settings_text(user: dict) -> str:
    role = user.get("role", "student")
    role_label = "👨‍🎓 Студент" if role == "student" else "👨‍🏫 Викладач"
    full_name = user.get("full_name") or "<i>не вказано</i>"
    group = user.get("group_name") or "<i>не вказана</i>"
    sem = user.get("semestr", 2)
    before = user.get("notify_before", 15)
    evening = "✅" if user.get("notify_evening") else "❌"
    notif = "✅" if user.get("notifications_on") else "❌"

    lines = [
        "⚙️ <b>Налаштування</b>\n",
        f"👤 ПІБ: <b>{full_name}</b>",
        f"🎭 Роль: <b>{role_label}</b>",
    ]
    if role == "student":
        lines.append(f"🏫 Група: <b>{group}</b>")
    lines += [
        f"📚 Семестр: <b>{sem}</b>",
        f"⏰ Сповіщення за: <b>{before} хв</b>",
        f"🌙 Вечірнє нагадування: <b>{evening}</b>",
        f"🔔 Сповіщення: <b>{notif}</b>",
    ]
    return "\n".join(lines)


def cabinet_text(user: dict) -> str:
    role = user.get("role", "student")
    role_label = "👨‍🎓 Студент" if role == "student" else "👨‍🏫 Викладач"
    full_name = user.get("full_name") or "<i>не вказано</i>"
    hint = ""
    if role == "teacher" and not user.get("full_name"):
        hint = "\n\n⚠️ <b>Для перегляду розкладу викладача необхідно вказати ПІБ повністю</b> (наприклад: Іваненко Іван Іванович)"
    return (
        f"👤 <b>Особистий кабінет</b>\n\n"
        f"ПІБ: <b>{full_name}</b>\n"
        f"Роль: <b>{role_label}</b>"
        f"{hint}"
    )


# ─── Handlers ──────────────────────────────────────────────────────────────────

async def show_settings(target, user: dict, edit: bool = False):
    text = settings_text(user)
    kb = main_settings_keyboard(user)
    if edit and isinstance(target, CallbackQuery):
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        msg = target.message if isinstance(target, CallbackQuery) else target
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)


async def show_cabinet(callback: CallbackQuery, user: dict, edit: bool = True):
    text = cabinet_text(user)
    kb = cabinet_keyboard(user)
    if edit:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == "⚙️ Налаштування")
async def cmd_settings(message: Message):
    await upsert_user(message.from_user.id)
    user = await get_user(message.from_user.id)
    await show_settings(message, user)


# ─── Особистий кабінет ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "open_cabinet")
async def cb_open_cabinet(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    await show_cabinet(callback, user)
    await callback.answer()


@router.callback_query(F.data == "back_to_settings")
async def cb_back_to_settings(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    await show_settings(callback, user, edit=True)
    await callback.answer()


@router.callback_query(F.data == "set_role")
async def cb_set_role(callback: CallbackQuery):
    await callback.message.answer("🎭 Оберіть вашу роль:", reply_markup=role_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("role_"))
async def process_role(callback: CallbackQuery):
    role = callback.data.split("_")[1]  # "student" або "teacher"
    await upsert_user(callback.from_user.id, role=role)
    user = await get_user(callback.from_user.id)
    await callback.message.delete()
    await show_cabinet(callback, user, edit=False)
    label = "Студент" if role == "student" else "Викладач"
    await callback.answer(f"Роль: {label} ✅")


@router.callback_query(F.data == "set_full_name")
async def cb_set_full_name(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    role = user.get("role", "student")
    if role == "teacher":
        hint = "Введіть ПІБ <b>повністю</b> (наприклад: <b>Іваненко Іван Іванович</b>):"
    else:
        hint = "Введіть ваше ім'я або ПІБ (наприклад: <b>Іван Іваненко</b>):"
    await callback.message.answer(f"✏️ {hint}", parse_mode="HTML")
    await state.set_state(SettingsStates.waiting_full_name)
    await callback.answer()


@router.message(SettingsStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await upsert_user(message.from_user.id, full_name=name)
    await state.clear()
    user = await get_user(message.from_user.id)
    await message.answer(f"✅ ПІБ збережено: <b>{name}</b>", parse_mode="HTML")
    await show_settings(message, user)


# ─── Група (тільки для студентів) ──────────────────────────────────────────────

@router.callback_query(F.data == "set_group")
async def cb_set_group(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✏️ Введіть назву вашої групи (наприклад: <b>КБ-407</b>):", parse_mode="HTML")
    await state.set_state(SettingsStates.waiting_group)
    await callback.answer()


@router.message(SettingsStates.waiting_group)
async def process_group(message: Message, state: FSMContext):
    group = message.text.strip().upper()
    await upsert_user(message.from_user.id, group_name=group)
    await state.clear()
    user = await get_user(message.from_user.id)
    await message.answer(f"✅ Групу встановлено: <b>{group}</b>", parse_mode="HTML")
    await show_settings(message, user)


# ─── Семестр ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "set_semestr")
async def cb_set_semestr(callback: CallbackQuery):
    await callback.message.answer("📚 Оберіть семестр:", reply_markup=semestr_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("semestr_"))
async def process_semestr(callback: CallbackQuery):
    sem = int(callback.data.split("_")[1])
    await upsert_user(callback.from_user.id, semestr=sem)
    user = await get_user(callback.from_user.id)
    await callback.message.delete()
    await show_settings(callback, user)
    await callback.answer(f"Семестр {sem} ✅")


# ─── Сповіщення ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "set_notify_before")
async def cb_set_notify_before(callback: CallbackQuery):
    await callback.message.answer("⏰ За скільки хвилин сповіщати про пару?", reply_markup=notify_before_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("before_"))
async def process_notify_before(callback: CallbackQuery):
    minutes = int(callback.data.split("_")[1])
    await upsert_user(callback.from_user.id, notify_before=minutes)
    user = await get_user(callback.from_user.id)
    await callback.message.delete()
    await show_settings(callback, user)
    await callback.answer(f"Сповіщення за {minutes} хв ✅")


@router.callback_query(F.data == "toggle_evening")
async def cb_toggle_evening(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    await upsert_user(callback.from_user.id, notify_evening=0 if user.get("notify_evening") else 1)
    user = await get_user(callback.from_user.id)
    await show_settings(callback, user, edit=True)
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def cb_toggle_notifications(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    await upsert_user(callback.from_user.id, notifications_on=0 if user.get("notifications_on") else 1)
    user = await get_user(callback.from_user.id)
    await show_settings(callback, user, edit=True)
    await callback.answer()


# ─── Назад ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "settings_back")
async def cb_settings_back(callback: CallbackQuery):
    from bot.keyboards import MAIN_MENU
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("🏠 Головне меню", reply_markup=MAIN_MENU)
    await callback.answer()
