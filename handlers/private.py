import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InputMediaPhoto
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from database.queries import orm_add_user, orm_get_admins, orm_get_user, orm_set_admin
from keyboards.admin import get_back_button, get_main_menu, register_menu, admin_subscription_menu, become_admin_button
from utils.utils import get_valid_file

router = Router()

# ✅ Настройки логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 📌 Состояния FSM для регистрации
class RegistrationState(StatesGroup):
    waiting_for_phone = State()




################## /START + Регистрация ##################  

@router.message(Command("start"))
async def start_command(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name or "Без имени"

    # ✅ Проверяем, зарегистрирован ли пользователь
    user = await orm_get_user(session, user_id)

    if user:
        # ✅ Если зарегистрирован, показываем меню
        await message.answer("✅ Вы уже зарегистрированы!\n\nВыберите действие:", reply_markup=get_main_menu())
        return

    # ✅ Отправляем баннер регистрации
    banner = get_valid_file("media/register_banner.jpg")
    if banner:
        await message.answer_photo(
            photo=banner,
            caption="👋 <b>Добро пожаловать!</b>\n\nДля работы с ботом вам нужно зарегистрироваться.",
            reply_markup=register_menu()
        )
    else:
        await message.answer("👋 <b>Добро пожаловать!</b>\n\nДля работы с ботом вам нужно зарегистрироваться.", reply_markup=register_menu())

# ✅ Кнопка "Зарегистрироваться"
@router.callback_query(F.data == "register_user")
async def register_user(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RegistrationState.waiting_for_phone)

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📞 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer("📲 Пожалуйста, отправьте ваш номер телефона, используя кнопку ниже.", reply_markup=keyboard)


# ✅ Получаем номер телефона
@router.message(RegistrationState.waiting_for_phone, F.contact)
async def get_phone_number(message: types.Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id
    username = message.from_user.username or "Не указан"
    phone_number = message.contact.phone_number

    # ✅ Регистрируем пользователя
    await orm_add_user(session, user_id, username, phone_number, is_admin=False)

    await message.answer(f"✅ <b>Вы успешно зарегистрированы!</b>\n\n📌 Ваш номер: {phone_number}", reply_markup=types.ReplyKeyboardRemove())

    # ✅ Кнопка "Стать администратором"
    await message.answer(
        "🚀 Хотите стать администратором?",
        reply_markup=become_admin_button()
    )

    await state.clear()




################## СТАТЬ АДМИНИСТРАТОРОМ ##################  

@router.callback_query(F.data == "become_admin")
async def become_admin(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id

    # ✅ Проверяем, зарегистрирован ли пользователь
    user = await orm_get_user(session, user_id)
    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь!", show_alert=True)
        return

    # ✅ Проверяем количество администраторов
    admins = await orm_get_admins(session)

    if len(admins) < 15:
        # ✅ Назначаем пользователя администратором
        await orm_set_admin(session, user_id)
        await session.commit()
        await callback.message.answer("✅ Вы стали администратором!\n\nВыберите действие:", reply_markup=get_main_menu())
    else:
        # ✅ Предлагаем подписку
        banner = get_valid_file("media/admin_subscription.jpg")
        if banner:
            await callback.message.answer_photo(
                photo=banner,
                caption="🔥 Все бесплатные места заняты!\n\nВы можете оформить подписку за <b>$10/месяц</b>.",
                reply_markup=admin_subscription_menu()
            )
        else:
            await callback.message.answer(
                "🔥 Все бесплатные места заняты!\n\nВы можете оформить подписку за <b>$10/месяц</b>.",
                reply_markup=admin_subscription_menu()
            )

################## ПРОЧЕЕ ##################  
@router.callback_query(F.data == "about_bot")
async def about_bot(callback: types.CallbackQuery):
    await callback.answer()

    banner = get_valid_file("media/about_bot_banner.jpg")
    if not banner:
        await callback.answer("❌ Файл 'about_bot_banner.jpg' не найден!", show_alert=True)
        return

    description = (
        "🤖 **О боте**\n\n"
        "Этот бот автоматически переводит сообщения в каналах, сохраняя форматирование и медиа.\n\n"
        "🔹 **Как подключить канал?**\n"
        "1️⃣ Добавьте бота в администраторы своего канала.\n"
        "2️⃣ Добавьте свои каналы в бот через админ панель.\n"
        "3️⃣ Выбрать главный канал в настройках бота.\n"
        "5️⃣ Дайте ему разрешение читать и публиковать сообщения.\n"
        "6️⃣ Включите перевод в настройках бота.\n\n"
        "После этого бот начнёт переводить новые сообщения автоматически! 🔄"
    )

    await callback.message.edit_media(
        media=InputMediaPhoto(media=banner, caption=description, parse_mode="Markdown"),
        reply_markup=get_back_button()
    )




# ✅ Кнопка "Назад"
@router.callback_query(F.data == "go_back")
async def go_back(callback: types.CallbackQuery):
    await callback.answer()
    
    banner = get_valid_file("media/main_banner.jpg")
    if not banner:
        await callback.answer("❌ Файл 'main_banner.jpg' не найден!", show_alert=True)
        return

    await callback.message.edit_media(
        media=InputMediaPhoto(media=banner, caption="👋 Добро пожаловать!\nВыберите действие:"),
        reply_markup=get_main_menu()
    )
