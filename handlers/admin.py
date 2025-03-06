import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database.models import Channel, Settings
from database.queries import orm_add_channel, orm_delete_channel, orm_get_admins, orm_get_all_channels, orm_get_statistics, orm_get_user, orm_set_setting
from sqlalchemy.ext.asyncio import AsyncSession
from utils.utils import get_valid_file

from keyboards.admin import get_admin_menu, get_back_button, get_settings_keyboard


router = Router()



AUTO_TRANSLATE_STATE = False  # ✅ Глобальная переменная для автоперевода



# Панель администратора
@router.message(Command("admin"))
async def admin_command(message: types.Message):
    if message.from_user.id not in orm_get_admins():
        await message.answer("⛔ У вас нет прав на управление ботом.")
        return

    await message.answer("📌 Панель управления каналами:", reply_markup=get_admin_menu())




# Обрабатываем кнопки администратора
@router.callback_query(F.data == "admin_panel")
async def handle_admin_buttons(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id

    # ✅ Получаем список админов из БД
    admin_ids = await orm_get_admins(session)

    if user_id in admin_ids:
        admin_banner = get_valid_file("media/admin_banner.jpg")
        if not admin_banner:
            await callback.answer("❌ Файл 'admin_banner.jpg' не найден! Проверь путь.", show_alert=True)
            return

        await callback.message.edit_media(
            media=InputMediaPhoto(media=admin_banner, caption="🛠 <b>Админ-панель</b>\n\nВыберите действие:"),
            reply_markup=get_admin_menu()
        )
    else:
        await callback.answer("⛔ У вас нет прав на вход в админ-панель.", show_alert=True)


# ✅ Обрабатываем кнопку "Вкл/Выкл автоперевод"
@router.callback_query(F.data == "toggle_auto_translate")
async def toggle_auto_translate(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id  # ✅ Получаем user_id

    # ✅ Проверяем текущее состояние автоперевода
    result = await session.execute(
        select(Settings.value).where(Settings.user_id == user_id, Settings.key == "AUTO_TRANSLATE_ENABLED")
    )
    current_status = result.scalar()

    # ✅ Переключаем статус
    new_status = "0" if current_status == "1" else "1"

    # ✅ Обновляем в БД
    await orm_set_setting(session, "AUTO_TRANSLATE_ENABLED", new_status, user_id)

    # ✅ Обновляем меню настроек
    await callback.message.edit_text(
        "⚙ <b>Настройки</b>\n\nВыберите нужный параметр:",
        reply_markup=await get_settings_keyboard(session, user_id)
    )

    await callback.answer(f"🔄 Автоперевод {'включен' if new_status == '1' else 'выключен'}!")




# ✅ Обрабатываем кнопку "Настройки"
@router.callback_query(F.data == "settings")
async def admin_settings(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id  # ✅ Получаем ID пользователя

    # ✅ Загружаем настройки с привязкой к пользователю
    keyboard = await get_settings_keyboard(session, user_id)

    await callback.message.answer("⚙ <b>Настройки</b>\n\nВыберите нужный параметр:", reply_markup=keyboard)


# ✅ Обрабатываем включение/выключение автоперевода
@router.callback_query(F.data == "toggle_autotranslate")
async def toggle_autotranslate(callback: types.CallbackQuery):
    global AUTO_TRANSLATE_STATE
    AUTO_TRANSLATE_STATE = not AUTO_TRANSLATE_STATE  # 🔄 Переключаем состояние

    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(AUTO_TRANSLATE_STATE)
    )

    await callback.answer(
        "✅ Автоперевод включён!" if AUTO_TRANSLATE_STATE else "❌ Автоперевод выключен!",
        show_alert=True
    )


# ✅ Обрабатываем кнопку "📊 Статистика"
@router.callback_query(F.data == "statistics")
async def admin_stats(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id  # ✅ Получаем user_id пользователя, который нажал кнопку

    # 🔥 Проверяем, есть ли у пользователя главный канал
    main_channel_result = await session.execute(select(Settings.value).where(
        Settings.user_id == user_id, Settings.key == "MAIN_CHANNEL_ID"
    ))
    main_channel_id = main_channel_result.scalar()

    if main_channel_id:
        # ✅ Если есть главный канал, получаем владельца
        owner_result = await session.execute(select(Channel.user_id).where(Channel.chat_id == int(main_channel_id)))
        owner_id = owner_result.scalar()
        
        if owner_id:
            print(f"🔄 Получаем статистику владельца канала user_id={owner_id}")
            stats_user_id = owner_id  # Используем владельца канала
        else:
            print(f"⚠ Главный канал найден, но владелец не определён, используем user_id={user_id}")
            stats_user_id = user_id
    else:
        print(f"⚠ Главный канал не найден, используем user_id={user_id}")
        stats_user_id = user_id  # Если нет канала, используем user_id пользователя

    # 🔥 Получаем статистику
    stats = await orm_get_statistics(session, stats_user_id)

    # ✅ Проверяем, если вся статистика == 0, показываем другое сообщение
    if stats.get("translated_messages", 0) == 0 and stats.get("total_words", 0) == 0 and stats.get("total_characters", 0) == 0:
        await callback.answer("⚠️ Статистика доступна только владельцу канала!", show_alert=True)
        return

    # ✅ Вывод статистики владельца
    await callback.message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"📩 <b>Переведённых сообщений:</b> <b>{stats.get('translated_messages')}</b>\n"
        f"📝 <b>Общее количество слов:</b> <b>{stats.get('total_words')}</b>\n"
        f"🔠 <b>Общее количество символов:</b> <b>{stats.get('total_characters')}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="settings")]
        ])
    )



# ✅ Обработчик кнопки "🔹 Выбрать главный канал"
@router.callback_query(F.data == "select_main_channel")
async def select_main_channel(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id 
    user_id = int(user_id)  # Приводим к int перед SQL-запросом
    channels = await orm_get_all_channels(session, user_id)

    if not channels:
        await callback.answer("❌ В базе нет каналов для выбора.", show_alert=True)
        return

    buttons = [
        [InlineKeyboardButton(text=f"🏆 {channel.name}", callback_data=f"set_main_{channel.chat_id}")]
        for channel in channels
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="settings")])  # Кнопка "Назад"

    await callback.message.answer("📌 Выберите главный канал:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))



# ✅ Устанавливаем новый главный канал
@router.callback_query(F.data.startswith("set_main_"))
async def set_main_channel(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id  # ✅ Получаем user_id

    new_main_channel_id = int(callback.data.split("_")[2])

    # ✅ Сохраняем новый главный канал в БД
    await orm_set_setting(session, "MAIN_CHANNEL_ID", str(new_main_channel_id), user_id)

    # ✅ Получаем название канала
    channels = await orm_get_all_channels(session, user_id)  # <-- Учёт пользователя
    main_channel_name = next((ch.name for ch in channels if ch.chat_id == new_main_channel_id), "Неизвестно")

    # ✅ Обновляем меню с учётом нового главного канала
    await callback.message.edit_text(
        f"⚙ <b>Настройки</b>\n\n🏆 Главный канал: {main_channel_name}\n\nВыберите нужный параметр:",
        reply_markup=await get_settings_keyboard(session, user_id)  # <-- Передаём user_id
    )

    await callback.answer(f"✅ Главный канал установлен: {main_channel_name}")








#############        Добавление канала         #############

# ✅ Состояния FSM для добавления канала
class AddChannelState(StatesGroup):
    waiting_for_channel = State()   # Ожидаем пересланное сообщение
    waiting_for_language = State()  # Ожидаем ввод языка


# ✅ Обрабатываем кнопку "➕ Добавить канал"
@router.callback_query(F.data == "add_channel")
async def add_channel(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    user_id = callback.from_user.id  # ✅ Получаем user_id из Telegram

    # ❌ Если пользователя нет в БД - показываем ошибку
    existing_user = await orm_get_user(session, user_id)
    if not existing_user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return

    # ✅ Просим пользователя переслать сообщение из канала
    await callback.message.answer("📩 Перешлите любое сообщение из канала, который хотите добавить.")
    await state.set_state(AddChannelState.waiting_for_channel)
    await state.update_data(user_id=user_id)  # ✅ Сохраняем user_id в FSM



# ✅ Ловим ВСЕ пересланные сообщения (текст, фото, видео, голосовые и т.д.)
@router.message(AddChannelState.waiting_for_channel)
async def get_channel_info(message: types.Message, state: FSMContext):    
    print(f"📩 Обработка пересланного сообщения из чата {message.chat.id}")

    if not message.forward_from_chat:
        await message.answer("❌ Это не сообщение из канала! Перешлите любое сообщение из нужного канала.")
        return

    chat_id = message.forward_from_chat.id
    chat_title = message.forward_from_chat.title or "Без названия"

    if message.forward_from_chat.type != "channel":
        await message.answer("❌ Это не канал! Перешлите сообщение из канала.")
        return

    print(f"✅ Канал найден: {chat_title} (ID: {chat_id})")

    await state.update_data(chat_id=chat_id, chat_title=chat_title)

    await message.answer(
        f"<b>Канал: {chat_title}</b>\n\n ID: {chat_id} \n\n✅ Найден \n\n\nТеперь введите язык канала\n('EN', 'DE', 'FR', 'ES', 'RU', 'IT', 'NL', 'PL', 'PT', 'JA', 'ZH')",
        parse_mode="HTML"
    )

    await state.set_state(AddChannelState.waiting_for_language)



# ✅ Пользователь вводит язык канала
@router.message(AddChannelState.waiting_for_language, F.text)
async def get_channel_language(message: types.Message, state: FSMContext, session: AsyncSession):
    language = message.text.strip().upper()

    if len(language) > 5:
        await message.answer("❌ Некорректный язык. Введите, например, EN, RU, FR")
        return

    data = await state.get_data()
    print(f"📊 FSM Data перед добавлением канала: {data}")  # ✅ Логируем данные

    user_id = data.get("user_id")
    chat_id = data.get("chat_id")
    chat_title = data.get("chat_title")

    if not user_id or not chat_id or not chat_title:
        await message.answer("❌ Произошла ошибка! Попробуйте заново.")
        return

    # Добавляем канал
    added = await orm_add_channel(session, user_id, chat_id, chat_title, language)

    if added:
        await message.answer(f"<b>Канал: {chat_title}</b>\n\n ID: {chat_id}\n Язык: {language}\n\n ✅ Добавлен", reply_markup=get_admin_menu())
    else:
        await message.answer("❌ Этот канал уже есть в базе данных.", reply_markup=get_admin_menu())

    await state.clear()






#############        Удаление канала         #############
# ✅ Показывает список каналов для удаления
@router.callback_query(F.data.startswith("delete_"))
async def admin_delete_channel(callback: types.CallbackQuery, session: AsyncSession):
    channel_id = callback.data.split("_")[1]  # Получаем ID удаляемого канала

    # 🔥 Удаляем канал из БД
    await orm_delete_channel(session, channel_id)

    # 🔄 Перезапрашиваем список каналов после удаления
    channels = await orm_get_all_channels(session, callback.from_user.id)  

    if not channels:
        await callback.message.edit_text("❌ В базе больше нет каналов.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button()]]))
        return

    # 🔁 Создаем новую клавиатуру с оставшимися каналами
    buttons = [
        [InlineKeyboardButton(text=f"❌ {channel.name}", callback_data=f"delete_{channel.chat_id}")]
        for channel in channels
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("📌 Выбери канал для удаления:", reply_markup=markup)



# ✅ Подтверждение удаления канала
@router.callback_query(F.data.startswith("delete_"))
async def confirm_delete_channel(callback: types.CallbackQuery, session: AsyncSession):
    chat_id = int(callback.data.split("_")[1])  # Получаем chat_id из callback_data
    deleted = await orm_delete_channel(session, chat_id)  # Удаляем канал из БД

    if deleted:
        # ✅ Получаем обновлённый список каналов
        channels = await orm_get_all_channels(session)

        if not channels:
            await callback.message.edit_text("❌ В базе больше нет каналов.")
            return

        # ✅ Создаём новую клавиатуру без удалённого канала
        buttons = (
            [InlineKeyboardButton(text=f"❌ {ch.name}", callback_data=f"delete_{ch.chat_id}")]
            for ch in channels
        )
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.answer("📌 Выбери канал для удаления:", reply_markup=markup)  # ✅ Обновляем список
    else:
        await callback.message.edit_text("❌ Ошибка: канал не найден.", reply_markup=get_back_button())

    await callback.answer()






# Показывает список каналов
@router.callback_query(F.data == "admin_list_channels")
async def admin_list_channels(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id  # ✅ Получаем user_id

    # ✅ Получаем ID главного канала
    result = await session.execute(
        select(Settings.value).where(Settings.user_id == user_id, Settings.key == "MAIN_CHANNEL_ID")
    )
    main_channel_id = result.scalar()

    # ✅ Получаем список каналов пользователя
    channels = await orm_get_all_channels(session, user_id)

    if not channels:
        await callback.answer("❌ У вас нет добавленных каналов.", show_alert=True)
        return

    # ✅ Создаём список каналов с короной для главного канала и языком
    text = "📋 <b>Список ваших каналов:</b>\n\n"
    for channel in channels:
        crown = "👑" if str(channel.chat_id) == main_channel_id else "▫️"
        text += f"{crown} <b>{channel.name}</b> ({channel.language})\n"

    # ✅ Отправляем новый ответ с кнопкой "Назад"
    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="go_back")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()  # ✅ Закрываем индикатор загрузки Telegram







# ✅ Возвращаем пользователя в главное админ-меню
@router.callback_query(F.data == "go_back")
async def go_back(callback: types.CallbackQuery):
    try:
        await callback.message.edit_text(
            "🔹 <b>Админ-панель</b>\n\nВыберите действие:",
            reply_markup=get_admin_menu()
        )
        await callback.answer()  # ✅ Закрываем индикатор загрузки в Telegram
    except Exception as e:
        print(f"Ошибка при обработке 'Назад': {e}")
