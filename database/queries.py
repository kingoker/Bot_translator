import asyncio
import traceback
from sqlalchemy import BigInteger, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.sql.expression import delete
from database.models import Channel, Settings, Statistics, User


# ✅ Получаем пользователя по chat_id
async def orm_get_user_by_channel(session: AsyncSession, chat_id: int):
    result = await session.execute(
        select(User).join(Channel, User.user_id == Channel.user_id).where(Channel.chat_id == chat_id).limit(1)
    )
    return result.scalar_one_or_none()


# Добавляем пользователя в БД
async def orm_add_user(session: AsyncSession, user_id: int, username: str, phone_number: str, is_admin: bool):
    new_user = User(user_id=user_id, username=username, phone_number=phone_number, is_admin=is_admin)
    session.add(new_user)
    await session.commit()



# ✅ Функция для получения пользователя по user_id
async def orm_get_user(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    return result.scalar()  # Должен вернуть объект User или None



# Назначаем пользователя администратором
async def orm_set_admin(session: AsyncSession, user_id: int):
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()

    if user:
        user.is_admin = True
        await session.commit()
        print(f"✅ Пользователь {user_id} теперь администратор")
        return True
    else:
        print(f"❌ Пользователь {user_id} не найден в базе")
        return False
    
    
# ✅ Получаем список всех админов (если их нет — возвращаем пустой список)
async def orm_get_admins(session: AsyncSession):
    result = await session.execute(
        select(User.user_id).filter(User.is_admin == True)  # ✅ Было: select(User) → select(User.user_id)
    )
    return [row[0] for row in result.fetchall()]





# ✅ Получаем пользователя по username и добавляем канал
async def orm_add_channel(session: AsyncSession, user_id: int, chat_id: int, name: str, language: str):
    try:
        print(f"🔍 Добавление канала: user_id={user_id}, chat_id={chat_id}, name={name}, language={language}")

        # Проверяем, есть ли канал в базе
        result = await session.execute(
            select(Channel).where(Channel.user_id == user_id, Channel.chat_id == chat_id)
        )
        existing_channel = result.scalar_one_or_none()

        if existing_channel:
            print(f"❌ Канал {chat_id} уже существует у user_id {user_id}")
            return False

        # Добавляем канал
        new_channel = Channel(user_id=user_id, chat_id=chat_id, name=name, language=language)
        session.add(new_channel)
        print("📌 Данные добавлены в сессию, готовим commit()...")

        await session.commit()  # 🔥 Здесь могло быть исключение
        print(f"✅ Канал {chat_id} добавлен в базу")
        return True

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"🔥 Ошибка при добавлении канала: {e}")
        return False


# Удаляем канал из БД
async def orm_delete_channel(session: AsyncSession, chat_id):
    try:
        chat_id = int(chat_id)  # ✅ Приводим `chat_id` к `int`
        result = await session.execute(
            select(Channel).where(Channel.chat_id == chat_id)
        )
        channel = result.scalar_one_or_none()

        if channel:
            await session.delete(channel)
            await session.commit()
            print(f"✅ Канал {chat_id} удален")
            return True
        else:
            print(f"⚠ Канал {chat_id} не найден в БД")
            return False

    except Exception as e:
        await session.rollback()
        print(f"❌ Ошибка при удалении канала: {e}")
        return False



# Получаем все каналы из БД
async def orm_get_all_channels(session, user_id: int):
    
    result = await session.execute(
        select(Channel).where(Channel.user_id == user_id)
    )
    
    return result.scalars().all()













###########     Настройки (автоперевод)      ###########

# ✅ Получить настройку
async def orm_get_setting(session: AsyncSession, key: str, user_id: int = None):
    if user_id:
        result = await session.execute(
            select(Settings.value).where(Settings.user_id == user_id, Settings.key == key)
        )
    else:
        result = await session.execute(
            select(Settings.value).where(Settings.key == key)  # 📌 Ищем без user_id
        )

    setting = result.scalar()

    if setting is None:
        print(f"⚠ Настройка {key} не найдена в БД.")
        return None, None

    return setting, key





# ✅ Установить настройку
async def orm_set_setting(session: AsyncSession, key: str, value: str, user_id: int):
    existing_setting = await session.execute(
        select(Settings).where(Settings.key == key, Settings.user_id == user_id)
    )
    setting = existing_setting.scalars().first()

    if setting:
        setting.value = value  # ✅ Обновляем значение
    else:
        new_setting = Settings(key=key, value=value, user_id=user_id)  # ✅ Создаем новую запись
        session.add(new_setting)

    await session.commit()





###########     Статистика      ###########

# ✅ Получаем текущую статистику
async def orm_get_statistics(session: AsyncSession, user_id: int):
    result = await session.execute(select(Statistics).where(Statistics.user_id == user_id))
    stat = result.scalars().first()

    if not stat:  # ✅ Если статистики нет, создаём её
        stat = Statistics(user_id=user_id, messages_sent=0, words_translated=0, characters_translated=0)
        session.add(stat)
        await session.commit()

    return {
        "translated_messages": stat.messages_sent,
        "total_words": stat.words_translated,
        "total_characters": stat.characters_translated
    }





# ✅ Обновляем статистику (увеличиваем счётчики)
async def orm_update_statistics(session: AsyncSession, user_id: int, text: str = None):
    try:
        print(f"🚀 Начинаем обновление статистики для user_id={user_id}")

        # 🔍 Проверяем, существует ли статистика
        result = await session.execute(select(Statistics).where(Statistics.user_id == user_id))
        stat = result.scalars().first()

        word_count = len(text.split()) if text else 0  # 🔥 Количество слов
        char_count = len(text) if text else 0  # 🔥 Количество символов

        if stat:
            print(f"🔄 Обновляем статистику для user_id={user_id}")
            stat.messages_sent += 1
            stat.words_translated += word_count
            stat.characters_translated += char_count
        else:
            print(f"🆕 Создаём статистику для user_id={user_id}")
            stat = Statistics(
                user_id=user_id,
                messages_sent=1,
                words_translated=word_count,
                characters_translated=char_count
            )
            session.add(stat)

        await session.flush()  # Применяем изменения в сессии
        await session.commit()  # ✅ Финальный коммит

        print(f"✅ Статистика обновлена для user_id={user_id}")

    except Exception as e:
        print(f"❌ Ошибка при обновлении статистики: {e}")
        traceback.print_exc()
        await session.rollback()  # Откатываем изменения в случае ошибки