import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from config import DB_URL

# Создаём асинхронный движок
engine = create_async_engine(DB_URL, echo=True)

# Фабрика сессий
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)




# Проверка подключения к БД
async def check_database_connection():
    try:
        conn = await asyncpg.connect(DB_URL.replace("postgresql+asyncpg", "postgres"))
        await conn.close()
        print("✅ Успешное подключение к БД!")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False

    
# Создаёт таблицы в БД
async def create_db():
    db_connected = await check_database_connection()

    if not db_connected:
        print("❌ База данных не найдена! Проверь подключение на хостинге.")
        return

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ Таблицы обновлены!")


# Удаляет все таблицы в БД
async def drop_db():
    confirm = input("⚠️ ВНИМАНИЕ! Вы уверены, что хотите удалить ВСЕ данные? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Операция отменена!")
        return

    async with engine.begin() as conn:
        print("⛔ Удаляем все таблицы...")
        await conn.run_sync(SQLModel.metadata.drop_all)
        print("✅ Таблицы успешно удалены!")

        print("🔄 Пересоздаём таблицы...")
        await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ База данных пересоздана!")

    print("🎯 БД очищена и готова к работе!")
