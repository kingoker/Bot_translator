from aiogram.dispatcher.middlewares.base import BaseMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import AsyncSessionLocal


# Middleware для передачи сессии SQLAlchemy в хэндлеры
class DatabaseSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with AsyncSessionLocal() as session:
            data["session"] = session  # ✅ Добавляем `session` в `data`
            return await handler(event, data)
