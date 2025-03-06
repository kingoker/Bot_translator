import sys
import os

# Добавляем корневую папку проекта в `sys.path`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import ADMIN_IDS
from aiogram.filters import BaseFilter
from aiogram.types import Message


# Фильтр для проверки является ли пользователь администратором
class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS
