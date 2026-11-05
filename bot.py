import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8837183643:AAGn77c7A2fWdi1H7S45vOa8DuFj6VYEcBk"
# Замените на свои ссылки
TERMS_URL = "https://telegra.ph/Ваша-ссылка-на-правила-01-01"
PRIVACY_URL = "https://telegra.ph/Ваша-ссылка-на-политику-01-01"
# Путь к картинке с осенними листьями. Положите картинку рядом с файлом main.py
WELCOME_IMAGE = "welcome.jpg" 

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Машина состояний для ожидания сообщения
class AnonState(StatesGroup):
    waiting_for_message = State()

# --- КЛАВИАТУРЫ ---
def get_cancel_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_anon")]
    ])
    return kb

# --- ОБРАБОТЧИКИ ---

# 1. Приветствие (как на 2 скрине)
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    text = (
        "<b>Что умеет этот бот?</b>\n\n"
        "В этом боте ты можешь получать анонимные* сообщения 🚀\n\n"
        f"📖 Пользовательское соглашение - <a href='{TERMS_URL}'>ссылка</a>\n"
        f"🔒 Политика конфиденциальности - <a href='{PRIVACY_URL}'>ссылка</a>\n\n"
        "<i>*Платные функции могут ограничивать анонимность</i>"
    )
    
    try:
        # Отправляем картинку с текстом
        photo = FSInputFile(WELCOME_IMAGE)
        await message.answer_photo(photo=photo, caption=text, parse_mode="HTML")
    except Exception as e:
        # Если картинки нет, отправим просто текст
        await message.answer(text=text, parse_mode="HTML")

    # Даем ссылку для получения анонимок
    bot_info = await bot.get_me()
    await message.answer(
        f"🔗 Ваша ссылка для сбора анонимок:\n"
        f"<code>https://t.me/{bot_info.username}?start=user_{message.from_user.id}</code>",
        parse_mode="HTML"
    )

# 2. Ловим переход по ссылке (когда человек хочет написать анонимку)
@dp.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: types.Message, command: CommandStart, state: FSMContext):
    # command.args содержит "user_12345678" (ID автора)
    args = command.args
    
    if args.startswith("user_"):
        author_id = args.split("_")[1]
        
        # Сохраняем ID автора в состояние
        await state.update_data(author_id=author_id)
        await state.set_state(AnonState.waiting_for_message)
        
        # Текст как на 1 скрине
        text = (
            "⚡️ <b>Анонимное сообщение для автора ссылки</b>\n\n"
            "💀 Напишите или отправьте здесь всё, что хотите*\n"
            "– отправитель останется неизвестным\n\n"
            "<b>Вы можете отправить</b> 📝 <i>текст</i>, 🎙 <i>голосовые</i>, 📸 <i>фото/видео</i>, "
            "🎥 <i>видеосообщения (кружки)</i>, 🏷 <i>стикеры</i> и тд"
        )
        
        await message.answer(text=text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    else:
        # Если перешли просто по ссылке без ID
        await cmd_start(message)

# 3. Обработка самого анонимного сообщения
@dp.message(AnonState.waiting_for_message, F.text | F.photo | F.video | F.voice | F.video_note | F.sticker)
async def process_anon_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    author_id = data.get("author_id")
    
    if not author_id:
        await message.answer("Ошибка: не найден получатель. Попробуйте перейти по ссылке заново.")
        await state.clear()
        return

    try:
        # Пересылаем сообщение автору БЕЗ указания отправителя (анонимно)
        # Используем copy_message, чтобы не было видно "Переслано от..."
        await bot.copy_message(
            chat_id=author_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        
        await message.answer("✅ Ваше сообщение отправлено анонимно!")
    except Exception as e:
        # Если автор заблокировал бота или не начинал с ним диалог
        await message.answer("⚠️ Не удалось отправить сообщение. Возможно, автор ограничил прием сообщений.")
        logging.error(f"Ошибка отправки анонимки: {e}")
    
    # Очищаем состояние после отправки
    await state.clear()

# 4. Обработка кнопки "Отменить"
@dp.callback_query(F.data == "cancel_anon")
async def cancel_anon(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отправка отменена.")
    await callback.answer()

# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
