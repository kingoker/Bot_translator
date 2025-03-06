import asyncio
from collections import defaultdict
from aiogram import Router
from aiogram.types import (
    Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument,
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.queries import orm_get_all_channels, orm_get_setting, orm_update_statistics
from services.translator import translate_text
from database.models import Channel

router = Router()

# Буфер для медиа-групп
media_group_buffer = defaultdict(list)
media_group_lock = defaultdict(asyncio.Lock)

async def translate_reply_markup(reply_markup, target_lang):
    """Переводит текст кнопок в inline-клавиатурах и обычных клавиатурах."""
    if not reply_markup:
        return None

    if isinstance(reply_markup, InlineKeyboardMarkup):
        new_inline_keyboard = []
        for row in reply_markup.inline_keyboard:
            new_row = []
            for button in row:
                translated_text = await translate_text(button.text, target_lang) if button.text else None
                new_row.append(
                    InlineKeyboardButton(
                        text=translated_text,
                        url=button.url if button.url else None,
                        callback_data=button.callback_data if button.callback_data else None
                    )
                )
            new_inline_keyboard.append(new_row)
        return InlineKeyboardMarkup(inline_keyboard=new_inline_keyboard)

    elif isinstance(reply_markup, ReplyKeyboardMarkup):
        new_keyboard = []
        for row in reply_markup.keyboard:
            new_row = [KeyboardButton(text=await translate_text(button.text, target_lang)) for button in row]
            new_keyboard.append(new_row)
        return ReplyKeyboardMarkup(keyboard=new_keyboard, resize_keyboard=True)

    return reply_markup

@router.channel_post()
async def auto_translate(message: Message, session: AsyncSession):
    """Обрабатывает сообщения из главного канала, переводит и отправляет в другие каналы пользователя."""

    main_channel = await orm_get_setting(session, "MAIN_CHANNEL_ID")
    main_channel_id = int(main_channel[0]) if main_channel and main_channel[0] else None

    if not main_channel_id or main_channel_id != message.chat.id:
        return

    owner_result = await session.execute(select(Channel.user_id).where(Channel.chat_id == main_channel_id).limit(1))
    owner_id = owner_result.scalar()

    if not owner_id:
        print(f"❌ Ошибка: Не найден владелец для канала {main_channel_id} в базе данных!")
        return
    else:
        print(f"✅ Найден владелец: user_id={owner_id}")

    channels = await orm_get_all_channels(session, owner_id)
    channels = [ch for ch in channels if ch.chat_id != main_channel_id]

    if not channels:
        return

    print(f"📩 Получено сообщение: {message.text or message.caption or 'Медиафайл'}")
    print(f"📄 Entities: {message.entities}")

    text_with_html = message.html_text or message.caption or ""
    reply_markup = message.reply_markup
    is_media_group = message.media_group_id is not None

    translated_texts = {ch.chat_id: await translate_text(text_with_html, ch.language) for ch in channels} if text_with_html else {}
    translated_markups = {ch.chat_id: await translate_reply_markup(reply_markup, ch.language) for ch in channels} if reply_markup else {}

    disable_web_page_preview = "http" in text_with_html or "https" in text_with_html

    # ✅ Обновляем статистику перед отправкой сообщений
    print(f"🔄 Обновляем статистику для user_id={owner_id}, текст: {text_with_html}")
    await orm_update_statistics(session, owner_id, text_with_html)
    print("✅ Статистика успешно обновлена!")

    if is_media_group:
        async with media_group_lock[message.media_group_id]:
            media_group_buffer[message.media_group_id].append(message)

            # Ожидание всех частей группы (1 секунда)
            await asyncio.sleep(1)

            # Сортируем сообщения по времени
            messages = sorted(media_group_buffer.pop(message.media_group_id, []), key=lambda m: m.date)

            for channel in channels:
                first_message = messages[0]
                remaining_messages = messages[1:]
                translated_text = translated_texts.get(channel.chat_id, None)
                translated_markup = translated_markups.get(channel.chat_id, None)

                if first_message.photo:
                    await message.bot.send_photo(
                        chat_id=channel.chat_id,
                        photo=first_message.photo[-1].file_id,
                        caption=translated_text,
                        parse_mode="HTML",
                        reply_markup=translated_markup
                    )
                elif first_message.video:
                    await message.bot.send_video(
                        chat_id=channel.chat_id,
                        video=first_message.video.file_id,
                        caption=translated_text,
                        parse_mode="HTML",
                        reply_markup=translated_markup
                    )
                elif first_message.document:
                    await message.bot.send_document(
                        chat_id=channel.chat_id,
                        document=first_message.document.file_id,
                        caption=translated_text,
                        parse_mode="HTML",
                        reply_markup=translated_markup
                    )

                media_group = []
                for msg in remaining_messages:
                    if msg.photo:
                        media_group.append(InputMediaPhoto(media=msg.photo[-1].file_id))
                    elif msg.video:
                        media_group.append(InputMediaVideo(media=msg.video.file_id))
                    elif msg.document:
                        media_group.append(InputMediaDocument(media=msg.document.file_id))

                if media_group:
                    await message.bot.send_media_group(
                        chat_id=channel.chat_id,
                        media=media_group
                    )
            return  

    for channel in channels:
        translated_text = translated_texts.get(channel.chat_id, None)
        translated_markup = translated_markups.get(channel.chat_id, None)

        if message.photo:
            await message.bot.send_photo(
                chat_id=channel.chat_id,
                photo=message.photo[-1].file_id,
                caption=translated_text,
                parse_mode="HTML",
                reply_markup=translated_markup
            )
        elif message.video:
            await message.bot.send_video(
                chat_id=channel.chat_id,
                video=message.video.file_id,
                caption=translated_text,
                parse_mode="HTML",
                reply_markup=translated_markup
            )
        elif message.document:
            await message.bot.send_document(
                chat_id=channel.chat_id,
                document=message.document.file_id,
                caption=translated_text,
                parse_mode="HTML",
                reply_markup=translated_markup
            )
        elif message.audio:
            await message.bot.send_audio(
                chat_id=channel.chat_id,
                audio=message.audio.file_id,
                caption=translated_text,
                parse_mode="HTML",
                reply_markup=translated_markup
            )
        elif message.voice:
            await message.bot.send_voice(
                chat_id=channel.chat_id,
                voice=message.voice.file_id,
                caption=translated_text,
                parse_mode="HTML",
                reply_markup=translated_markup
            )
        elif message.video_note:
            await message.bot.send_video_note(
                chat_id=channel.chat_id,
                video_note=message.video_note.file_id
            )
        elif message.sticker:
            await message.bot.send_sticker(
                chat_id=channel.chat_id,
                sticker=message.sticker.file_id
            )
        elif message.poll:
            await message.bot.send_poll(
                chat_id=channel.chat_id,
                question=message.poll.question,
                options=[option.text for option in message.poll.options],
                is_anonymous=message.poll.is_anonymous,
                allows_multiple_answers=message.poll.allows_multiple_answers
            )
        elif translated_text:
            await message.bot.send_message(
                chat_id=channel.chat_id,
                text=translated_text,
                parse_mode="HTML",
                reply_markup=translated_markup,
                disable_web_page_preview=disable_web_page_preview
            )

    print("✅ Сообщение переведено и отправлено в каналы!")