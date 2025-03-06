from aiogram import Router, types
import logging

router = Router()


# ✅ Логирование всех сообщений
@router.message()
async def log_messages(message: types.Message):
    logging.info(f"📩 Получено сообщение от {message.chat.id}: {message.text or 'Медиафайл'}")
