import os
from aiogram.types import FSInputFile


# ✅ Функция проверки файла
def get_valid_file(file_path: str):
    abs_path = os.path.abspath(file_path)  # ✅ Получаем абсолютный путь
    print(f"📂 Проверяем файл: {abs_path}")  # ✅ Выводим путь в консоль

    if not os.path.exists(abs_path):
        print(f"❌ Файл не найден: {abs_path}")  # ✅ Логируем отсутствие файла
        return None  # ❌ Файл не найден

    return FSInputFile(abs_path)  # ✅ Возвращаем `FSInputFile`