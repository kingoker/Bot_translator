from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Settings
from database.queries import orm_get_all_channels


# ✅ Клавиатура для регистрации
def register_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Зарегистрироваться", callback_data="register_user")]
])

# ✅ Меню для оплаты
def admin_subscription_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💳 Оформить подписку за $10", url="https://your-payment-link.com"),
        InlineKeyboardButton("💬 Связаться с разработчиком", url="https://t.me/king_designn")
    )
    return keyboard


def become_admin_button():
    return InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👑 Стать администратором", callback_data="become_admin")]
])


# Назад
def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="go_back")]
    ])

# Главное меню
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Админ-панель", callback_data="admin_panel")],
        [InlineKeyboardButton(text="ℹ О боте", callback_data="about_bot")]
    ])
    return keyboard


# Меню админнистратора
def get_admin_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton(text="❌ Удалить канал", callback_data="delete_channel")],
        [InlineKeyboardButton(text="📋 Список каналов", callback_data="admin_list_channels")],  # ✅ Убедись, что admin_list_channels
        [InlineKeyboardButton(text="🔙 Назад", callback_data="go_back")]  # ✅ Исправленная кнопка "Назад"
    ])
    return keyboard





# ✅ Клавиатура настроек
async def get_settings_keyboard(session: AsyncSession, user_id: int):
    # ✅ Получаем ID главного канала
    result = await session.execute(
        select(Settings.value).where(Settings.user_id == user_id, Settings.key == "MAIN_CHANNEL_ID")
    )
    main_channel_id = result.scalar()

    # ✅ Загружаем список каналов
    channels = await orm_get_all_channels(session, user_id)

    # ✅ Определяем название главного канала
    main_channel_name = "Не выбран"
    if main_channel_id:
        main_channel = next((ch for ch in channels if str(ch.chat_id) == main_channel_id), None)
        if main_channel:
            main_channel_name = f"👑 {main_channel.name}"  # ✅ Добавляем значок короны

    # ✅ Проверяем состояние автоперевода
    result = await session.execute(
        select(Settings.value).where(Settings.user_id == user_id, Settings.key == "AUTO_TRANSLATE_ENABLED")
    )
    auto_translate_status = result.scalar()
    auto_translate_text = "✅ Автоперевод: Включен" if auto_translate_status == "1" else "❌ Автоперевод: Выключен"

    # ✅ Создаём кнопки
    buttons = [
        [InlineKeyboardButton(text=f"🔹 Главный канал: {main_channel_name}", callback_data="select_main_channel")],
        [InlineKeyboardButton(text=auto_translate_text, callback_data="toggle_auto_translate")],  # ✅ Кнопка автоперевода
        [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="go_back")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


