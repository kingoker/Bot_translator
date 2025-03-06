import aiohttp
import os
import html
import re

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")

SUPPORTED_LANGUAGES = {"EN", "DE", "FR", "ES", "RU", "IT", "NL", "PL", "PT", "JA", "ZH"}

def prepare_text_for_translation(text):
    """Заменяем переводы строк на <br>, чтобы DeepL сохранял форматирование."""
    text = text.replace("\n", "<br>")  # Telegram использует \n, а DeepL лучше работает с <br>
    return text

def restore_line_breaks(text):
    """Восстанавливает отступы и абзацы в переведенном тексте."""
    text = re.sub(r'\s*<br\s*/?>\s*', '\n', text)  # Заменяем <br> на \n
    text = re.sub(r'\s*</?(p|div)>\s*', '\n\n', text)  # <p> и <div> превращаем в абзацы
    text = re.sub(r'\n{3,}', '\n\n', text)  # Убираем лишние пустые строки
    return text.strip()

async def deepL_translate(text, target_lang):
    """Отправляет запрос в DeepL API и получает перевод текста, сохраняя HTML-разметку и отступы."""
    url = "https://api-free.deepl.com/v2/translate"
    
    headers = {"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"}
    prepared_text = prepare_text_for_translation(text)  # Заменяем \n на <br>
    
    data = {
        "text": prepared_text,
        "target_lang": target_lang.upper(),
        "tag_handling": "html",  # Сообщаем DeepL, что текст содержит HTML
        "ignore_tags": "b, i, u, s, code, pre, a",  # Теги, которые НЕ нужно переводить
        "preserve_formatting": "1",  # Сохраняем пробелы и отступы
        "split_sentences": "nonewlines",  # Не разбиваем текст на новые строки
        "formality": "default"
    }

    print(f"🔄 Отправляем в DeepL ({target_lang}): {html.escape(prepared_text)}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=data) as response:
                result = await response.json()
                if response.status == 200 and "translations" in result:
                    translated_text = result["translations"][0]["text"]
                    translated_text = restore_line_breaks(translated_text)  # Восстанавливаем отступы
                    print(f"✅ Получили перевод ({target_lang}): {html.escape(translated_text)}")
                    return translated_text
                else:
                    print(f"⚠ Ошибка перевода ({target_lang}): {result}")
                    return f"⚠ Ошибка перевода ({target_lang})"
        except Exception as e:
            print(f"⚠ Ошибка API ({target_lang}): {e}")
            return f"⚠ Ошибка API ({target_lang})"

async def translate_text(text: str, target_lang: str) -> str:
    """Переводит текст через DeepL API, сохраняя форматирование и отступы."""
    
    if target_lang.upper() not in SUPPORTED_LANGUAGES:
        return f"⚠ Перевод недоступен для {target_lang.upper()}"

    translated_text = await deepL_translate(text, target_lang)
    return translated_text
