import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# ✅ Обязательные переменные
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")

# ✅ Проверяем, что ключи загружены
if not BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не задан в .env!")
if not DB_URL:
    print("❌ Ошибка: DATABASE_URL не задан в .env!")
if not DEEPL_API_KEY:
    print("⚠ Внимание: DEEPL_API_KEY не задан в .env (перевод может не работать).")
