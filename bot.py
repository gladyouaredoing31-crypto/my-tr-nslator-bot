import logging
import os
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8837183643:AAGivwNcHn0XlGkHKSnS8kNXqboA6fVga3M")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Хранилище в памяти: code -> owner_user_id
codes = {}
# user_id -> {"code": "...", "messages_received": 0}
owners = {}


def get_owner(user_id):
    if user_id not in owners:
        code = secrets.token_urlsafe(8)
        owners[user_id] = {"code": code, "messages_received": 0}
        codes[code] = user_id
    return owners[user_id]


# ============================================================
# /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Переход по ссылке — анонимное сообщение
    if context.args:
        code = context.args[0]
        if code in codes and codes[code] != user.id:
            # Пользователь перешёл по чужой ссылке — готов его принять
            context.user_data["sending_to"] = codes[code]
            await update.message.reply_text(
                "🚀 Здесь можно отправить анонимное сообщение человеку,\n"
                "который опубликовал эту ссылку.\n\n"
                "⚡ Напишите сюда всё, что хотите ему передать, и через несколько\n"
                "секунд он получит ваше сообщение, но не будет знать от кого.\n\n"
                "📝 Отправить можно: текст, фото, видео, стикеры, голосовые и\n"
                "видеосообщения (кружки)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить отправку", callback_data="cancel_send")
                ]])
            )
            return
        else:
            await update.message.reply_text("❌ Ссылка недействительна.")
            return

    # Обычный старт — это владелец
    o = get_owner(user.id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={o['code']}"

    text = (
        "👋 Привет! Это бот для анонимных вопросов.\n\n"
        "📢 **Как работает:**\n"
        "1️⃣ Опубликуй свою ссылку (ниже) в канале, чате или соцсетях\n"
        "2️⃣ Люди будут писать тебе анонимно\n"
        "3️⃣ Ты получишь сообщение сюда, но не узнаешь от кого\n\n"
        f"🔗 **Твоя ссылка:**\n`{link}`\n\n"
        "👇 Скопируй её и отправь куда хочешь."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# /my_link
# ============================================================
async def my_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    o = get_owner(user.id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={o['code']}"
    await update.message.reply_text(
        f"🔗 **Твоя ссылка:**\n\n`{link}`\n\n"
        f"📊 Получено сообщений: **{o['messages_received']}**",
        parse_mode="Markdown"
    )


# ============================================================
# /help
# ============================================================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **Помощь**\n\n"
        "/start — показать твою ссылку\n"
        "/my_link — снова показать ссылку + статистику\n"
        "/help — эта справка\n\n"
        "**Как пользоваться:**\n"
        "1. Получи ссылку через /start\n"
        "2. Опубликуй её где угодно\n"
        "3. Тебе будут писать анонимно\n"
        "4. Ты не узнаешь, кто именно написал",
        parse_mode="Markdown"
    )


# ============================================================
# КНОПКА ОТМЕНЫ
# ============================================================
async def cancel_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("sending_to", None)
    await query.edit_message_text("❌ Отправка отменена.")


# ============================================================
# ОБРАБОТКА СООБЩЕНИЙ
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Если это переход по чужой ссылке — отправляем владельцу
    if "sending_to" in context.user_data:
        owner_id = context.user_data["sending_to"]

        # Проверка — не владелец ли сам себе пишет
        if owner_id == user.id:
            await update.message.reply_text("❌ Нельзя писать самому себе.")
            return

        try:
            # Готовим подпись
            info_line = "\n\n💌 Анонимное сообщение"
            # Пересылаем в зависимости от типа
            if update.message.text:
                await context.bot.send_message(
                    chat_id=owner_id,
                    text=f"📨 **Анонимное сообщение:**\n\n{update.message.text}",
                    parse_mode="Markdown"
                )
            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=owner_id,
                    photo=update.message.photo[-1].file_id,
                    caption=f"📷 Анонимное фото{chr(10) + update.message.caption if update.message.caption else ''}"
                )
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=owner_id,
                    video=update.message.video.file_id,
                    caption=f"🎥 Анонимное видео{chr(10) + update.message.caption if update.message.caption else ''}"
                )
            elif update.message.voice:
                await context.bot.send_voice(
                    chat_id=owner_id,
                    voice=update.message.voice.file_id,
                    caption="🎤 Анонимное голосовое"
                )
            elif update.message.video_note:
                await context.bot.send_video_note(
                    chat_id=owner_id,
                    video_note=update.message.video_note.file_id
                )
            elif update.message.sticker:
                await context.bot.send_sticker(
                    chat_id=owner_id,
                    sticker=update.message.sticker.file_id
                )
            elif update.message.document:
                await context.bot.send_document(
                    chat_id=owner_id,
                    document=update.message.document.file_id,
                    caption=f"📎 Анонимный файл{chr(10) + update.message.caption if update.message.caption else ''}"
                )
            elif update.message.animation:
                await context.bot.send_animation(
                    chat_id=owner_id,
                    animation=update.message.animation.file_id,
                    caption=f"🎞️ Анонимная GIF"
                )
            else:
                await update.message.reply_text("❌ Такой тип сообщений не поддерживается.")
                return

            # Успех
            o = get_owner(owner_id)
            o["messages_received"] += 1
            await update.message.reply_text(
                "✅ Сообщение отправлено анонимно!\n\n"
                "Можешь отправить ещё одно или закрыть бота."
            )
        except Exception as e:
            logging.error(f"Ошибка: {e}")
            await update.message.reply_text(
                "❌ Не удалось отправить. Возможно, получатель заблокировал бота."
            )
        return

    # Обычное сообщение владельцу (не в режиме отправки)
    await update.message.reply_text(
        "💬 Ты сейчас не отправляешь анонимку.\n\n"
        "Чтобы получить свою ссылку для анонимных вопросов — /start\n"
        "Чтобы ответить кому-то — нужно перейти по его ссылке."
    )


# ============================================================
# ЗАПУСК
# ============================================================
def main():
    if not BOT_TOKEN or BOT_TOKEN == "СЮДА_ВСТАВЬ_СВОЙ_ТОКЕН":
        print("❌ Нет токена!")
        return
    print("🚀 Бот анонимных вопросов запущен...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("my_link", my_link))
    app.add_handler(CallbackQueryHandler(cancel_send, pattern="^cancel_send$"))
    app.add_handler(MessageHandler(
        ~filters.COMMAND & (
            filters.TEXT | filters.PHOTO | filters.VIDEO |
            filters.VOICE | filters.VIDEO_NOTE | filters.Sticker.ALL |
            filters.Document.ALL | filters.ANIMATION
        ),
        handle_message
    ))

    print("✅ Готов!")
    app.run_polling()


if __name__ == "__main__":
    main()
