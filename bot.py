import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("8837183643:AAGn77c7A2fWdi1H7S45vOa8DuFj6VYEcBk")
TERMS_URL = "https://telegra.ph/Ваша-ссылка-на-правила-01-01"
PRIVACY_URL = "https://telegra.ph/Ваша-ссылка-на-политику-01-01"
WELCOME_IMAGE = "welcome.jpg" 

# ВАЖНО: Сюда впиши ID тех трех человек, кому должны приходить анонимки
# Узнать ID можно через бота @userinfobot
ADMIN_IDS = ["7599142732","1673532605"] # ЗАМЕНИ НА РЕАЛЬНЫЕ ID!

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class AnonState(StatesGroup):
    waiting_for_message = State()

def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_anon")]
    ])

# 1. Приветствие и ВЫДАЧА ССЫЛКИ ДЛЯ КАНАЛА (только для админов)
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id_str = str(message.from_user.id)
    
    # Если зашел админ - показываем ему меню и ссылку для канала
    if user_id_str in ADMIN_IDS:
        text = (
            "<b>Панель администратора</b> 👑\n\n"
            "Скопируй ссылку ниже и скинь её в свой канал. "
            "Все, кто перейдет по ней, смогут написать анонимно сразу всем админам!"
        )
        
        # Формируем ссылку из всех ID админов через запятую
        ids_string = ",".join(ADMIN_IDS)
        bot_info = await bot.get_me()
        channel_link = f"https://t.me/{bot_info.username}?start=user_{ids_string}"
        
        await message.answer(
            f"{text}\n\n🔗 <b>Твоя ссылка для канала:</b>\n"
            f"<code>{channel_link}</code>",
            parse_mode="HTML"
        )
    else:
        # Если зашел обычный человек (не админ) - показываем ему инфо
        text = (
            "<b>Что умеет этот бот?</b>\n\n"
            "Здесь ты можешь отправлять анонимные сообщения 🚀\n\n"
            f"📖 Правила - <a href='{TERMS_URL}'>ссылка</a>\n"
            f"🔒 Политика - <a href='{PRIVACY_URL}'>ссылка</a>"
        )
        try:
            photo = FSInputFile(WELCOME_IMAGE)
            await message.answer_photo(photo=photo, caption=text, parse_mode="HTML")
        except Exception:
            await message.answer(text=text, parse_mode="HTML")

# 2. Переход по ссылке из канала (любой человек)
@dp.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: types.Message, command: CommandStart, state: FSMContext):
    args = command.args
    
    if args.startswith("user_"):
        ids_string = args.replace("user_", "")
        author_ids = [uid.strip() for uid in ids_string.split(",") if uid.strip()]
        
        if not author_ids:
            await message.answer("Ошибка: неверная ссылка.")
            return

        # Сохраняем список ID (в нашем случае это 3 админа)
        await state.update_data(author_ids=author_ids)
        await state.set_state(AnonState.waiting_for_message)
        
        text = (
            "⚡️ <b>Анонимное сообщение</b>\n\n"
            "💀 Напишите или отправьте здесь всё, что хотите*\n"
            "– отправитель останется неизвестным\n\n"
            "<b>Вы можете отправить</b> 📝 <i>текст</i>, 🎙 <i>голосовые</i>, 📸 <i>фото/видео</i>, "
            "🎥 <i>видеосообщения</i>, 🏷 <i>стикеры</i> и тд"
        )
        
        await message.answer(text=text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    else:
        await cmd_start(message)

# 3. Отправка анонимки админам
@dp.message(AnonState.waiting_for_message, F.text | F.photo | F.video | F.voice | F.video_note | F.sticker)
async def process_anon_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    author_ids = data.get("author_ids", [])
    
    if not author_ids:
        await message.answer("Ошибка: не найден получатель.")
        await state.clear()
        return

    success_count = 0
    for author_id in author_ids:
        try:
            await bot.copy_message(
                chat_id=author_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Ошибка отправки для ID {author_id}: {e}")

    if success_count > 0:
        await message.answer(f"✅ Сообщение отправлено анонимно!")
    else:
        await message.answer("⚠️ Не удалось отправить. Возможно, админы не нажали /start в боте.")
    
    await state.clear()

@dp.callback_query(F.data == "cancel_anon")
async def cancel_anon(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отправка отменена.")
    await callback.answer()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
