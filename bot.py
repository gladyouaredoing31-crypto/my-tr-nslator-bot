import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

# ================= НАСТРОЙКИ =================
BOT_TOKEN ="8837183643:AAGn77c7A2fWdi1H7S45vOa8DuFj6VYEcBk"

# Ссылки (замени на свои)
TERMS_URL = "https://telegra.ph/Правила-01-01"
PRIVACY_URL = "https://telegra.ph/Политика-01-01"
WELCOME_IMAGE = "welcome.jpg" 

# ID админов (кому будут приходить анонимки). ВАЖНО: строго строки в кавычках!
ADMIN_IDS = ["1673532605", "7599142732", "333333333"] # <-- ЗАМЕНИ НА СВОИ ID

# ================= ИНИЦИАЛИЗАЦИЯ =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class AnonState(StatesGroup):
    waiting_for_message = State()

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить отправку", callback_data="cancel_anon")]
    ])

# ================= 1. СТАРТ (АДМИНЫ И ЮЗЕРЫ) =================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id_str = str(message.from_user.id)
    
    # Если зашел АДМИН — показываем панель и ссылку для канала
    if user_id_str in ADMIN_IDS:
        bot_info = await bot.get_me()
        # Генерируем ссылку со всеми ID админов
        admin_ids_str = ",".join(ADMIN_IDS)
        channel_link = f"https://t.me/{bot_info.username}?start=user_{admin_ids_str}"
        
        text = (
            "<b>👑 Панель администратора</b>\n\n"
            "Скопируй ссылку ниже и отправь её в канал.\n"
            "Все, кто перейдет по ней, смогут написать анонимно сразу всем админам.\n\n"
            f"🔗 <b>Ссылка для канала:</b>\n<code>{channel_link}</code>"
        )
        await message.answer(text, parse_mode="HTML")
        return

    # Если зашел ОБЫЧНЫЙ ЮЗЕР
    text = (
        "<b>Что умеет этот бот?</b>\n\n"
        "В этом боте ты можешь отправлять анонимные сообщения 🚀\n\n"
        f"📖 <a href='{TERMS_URL}'>Пользовательское соглашение</a>\n"
        f"🔒 <a href='{PRIVACY_URL}'>Политика конфиденциальности</a>\n\n"
        "<i>*Платные функции могут ограничивать анонимность</i>"
    )
    
    try:
        photo = FSInputFile(WELCOME_IMAGE)
        await message.answer_photo(photo=photo, caption=text, parse_mode="HTML")
    except Exception as e:
        logging.warning(f"Картинка не найдена или ошибка отправки: {e}")
        await message.answer(text=text, parse_mode="HTML")

# ================= 2. ПЕРЕХОД ПО ССЫЛКЕ ИЗ КАНАЛА =================
@dp.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: Message, command: CommandStart, state: FSMContext):
    args = command.args
    
    if args.startswith("user_"):
        ids_string = args.replace("user_", "")
        author_ids = [uid.strip() for uid in ids_string.split(",") if uid.strip()]
        
        if not author_ids:
            await message.answer("⚠️ Ошибка: неверная ссылка. Попробуйте перейти заново.")
            return

        # Сохраняем ID получателей в сессию пользователя
        await state.update_data(author_ids=author_ids)
        await state.set_state(AnonState.waiting_for_message)
        
        text = (
            "⚡️ <b>Анонимное сообщение</b>\n\n"
            "💀 Напишите или отправьте здесь всё, что хотите*\n"
            "– отправитель останется неизвестным\n\n"
            "<b>Вы можете отправить</b> 📝 <i>текст</i>, 🎙 <i>голосовые</i>, 📸 <i>фото/видео</i>, "
            "🎥 <i>видеосообщения (кружки)</i>, 🏷 <i>стикеры</i> и тд"
        )
        
        await message.answer(text=text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    else:
        # Если перешли без параметра
        await cmd_start(message)

# ================= 3. ПРИЕМ И РАССЫЛКА АНОНИМКИ =================
@dp.message(AnonState.waiting_for_message)
async def process_anon_message(message: Message, state: FSMContext):
    data = await state.get_data()
    author_ids = data.get("author_ids", [])
    
    if not author_ids:
        await message.answer("⚠️ Сессия истекла. Перейдите по ссылке из канала заново.")
        await state.clear()
        return

    success_count = 0
    failed_count = 0

    # Отправляем всем админам
    for author_id in author_ids:
        try:
            await bot.copy_message(
                chat_id=author_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success_count += 1
        except TelegramForbiddenError:
            # Админ заблокировал бота
            failed_count += 1
            logging.warning(f"Админ {author_id} заблокировал бота.")
        except Exception as e:
            failed_count += 1
            logging.error(f"Ошибка отправки для {author_id}: {e}")

    # Отвечаем отправителю
    if success_count > 0:
        await message.answer("✅ <b>Сообщение успешно отправлено анонимно!</b>", parse_mode="HTML")
    else:
        await message.answer("⚠️ Не удалось доставить сообщение. Возможно, получатели ограничили прием.")
    
    # Очищаем состояние после отправки
    await state.clear()

# ================= 4. ОТМЕНА =================
@dp.callback_query(F.data == "cancel_anon")
async def cancel_anon(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ <b>Отправка отменена.</b>", parse_mode="HTML")
    except TelegramBadRequest:
        pass # Если сообщение уже было удалено
    await callback.answer("Действие отменено")

# ================= ЗАПУСК =================
async def main():
    logging.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
