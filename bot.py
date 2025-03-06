import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares.db import DatabaseSessionMiddleware

from config import BOT_TOKEN
from database.db import create_db, drop_db
from handlers import translator, admin, private, logger  # ✅ Убрали лишние обработчики

# ✅ Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# ✅ Создаём бота с HTML-парсингом
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# ✅ Добавляем middleware для базы данных
dp.update.middleware(DatabaseSessionMiddleware())

# ✅ Регистрируем обработчики
dp.include_router(private.router)
dp.include_router(translator.router)
dp.include_router(admin.router)
dp.include_router(logger.router)


# ✅ Запускаем бота
async def main():
    await create_db()  # ✅ Создаём базу данных перед запуском бота

    print("✅ Запустили бота")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())  # ✅ Стандартный запуск
