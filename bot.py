import logging
import os
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8837183643:AAGn77c7A2fWdi1H7S45vOa8DuFj6VYEcBk")

# ============================================================
# ТВОЙ TELEGRAM ID (узнать через @userinfobot)
# ============================================================
ADMIN_ID = 1673532605  # ← ЗАМЕНИ НА СВОЙ ID, например: ADMIN_ID = 123456789

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

codes = {}
owners = {}


def get_owner(user_id):
    if user_id not in owners:
        code = secrets.token_urlsafe(4)
        owners[user_id] = {
            "code": code,
            "messages_received": 0,
            "first_seen": None,
            "last_seen": None,
            "username": None,
        }
        codes[code] = user_id
    return owners[user_id]


# ============================================================
# /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import time
    user = update.effective_user

    if context.args:
        code = context.args[0]
        if code in codes and codes[code] != user.id:
            context.user_data["sending_to"] = codes[code]
            await update.message.reply_text(
                "🚀 Здесь можно отправить анонимное сообщение человеку,\n"
                "который опубликовал эту ссылку.\n\n"
                "⚡ Напиши сюда всё, что хочешь ему передать, и через несколько\n"
                "секунд он получит твоё сообщение, но не будет знать от кого.\n\n"
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

    o = get_owner(user.id)
    now = int(time.time())
    if not o["first_seen"]:
        o["first_seen"] = now
    o["last_seen"] = now
    o["username"] = user.username or user.first_name or str(user.id)

    bot_username = (await context.bot.get_me()).username
    link = "https://t.me/" + bot_username + "?start=" + o["code"]

    text = (
        "👋 Привет! Это бот для анонимных вопросов.\n\n"
        "📢 Как работает:\n"
        "1️⃣ Опубликуй свою ссылку (ниже) в канале, чате или соцсетях\n"
        "2️⃣ Люди будут писать тебе анонимно\n"
        "3️⃣ Ты получишь сообщение сюда, но не узнаешь от кого\n\n"
        "🔗 Твоя ссылка:\n" + link + "\n\n"
        "👇 Скопируй её и отправь куда хочешь."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Скопировать ссылку", callback_data="copy_link")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
    ])

    await update.message.reply_text(text, reply_markup=keyboard)


# ============================================================
# /help
# ============================================================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Помощь\n\n"
        "/start — показать твою ссылку\n"
        "/my_link — снова показать ссылку + статистику\n"
        "/help — эта справка\n\n"
        "Как пользоваться:\n"
        "1. Получи ссылку через /start\n"
        "2. Опубликуй её где угодно\n"
        "3. Тебе будут писать анонимно\n"
        "4. Ты не узнаешь, кто именно написал"
    )


# ============================================================
# /my_link
# ============================================================
async def my_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    o = get_owner(user.id)
    bot_username = (await context.bot.get_me()).username
    link = "https://t.me/" + bot_username + "?start=" + o["code"]
    await update.message.reply_text(
        "🔗 Твоя ссылка:\n\n" + link + "\n\n"
        "📊 Получено сообщений: " + str(o["messages_received"]),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Скопировать", callback_data="copy_link")]
        ])
    )


# ============================================================
# /stats — СЕКРЕТНАЯ КОМАНДА ДЛЯ АДМИНА
# ============================================================
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика — видит ТОЛЬКО админ"""
    user = update.effective_user

    # Если это не админ — молча выходим (бот как будто не знает команду)
    if user.id != ADMIN_ID:
        return

    import time
    now = int(time.time())

    total_users = len(owners)
    total_messages = sum(o["messages_received"] for o in owners.values())

    # Сколько активных за 24 часа
    active_24h = sum(1 for o in owners.values() if o["last_seen"] and now - o["last_seen"] < 86400)

    text = (
        "📊 <b>СТАТИСТИКА БОТА</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "👥 <b>Всего пользователей:</b> " + str(total_users) + "\n"
        "📨 <b>Всего анонимок:</b> " + str(total_messages) + "\n"
        "🔥 <b>Активных за 24ч:</b> " + str(active_24h) + "\n\n"
    )

    # Топ-5 по анонимкам
    if owners:
        top = sorted(owners.items(), key=lambda x: -x[1]["messages_received"])[:5]
        text += "🏆 <b>Топ-5 по анонимкам:</b>\n"
        for i, (uid, o) in enumerate(top):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else str(i + 1) + "."
            username = o.get("username") or str(uid)
            text += medal + " " + username + " — " + str(o["messages_received"]) + " шт.\n"
        text += "\n"

    # Последние 5 активных
    if owners:
        recent = sorted(
            [(uid, o) for uid, o in owners.items() if o["last_seen"]],
            key=lambda x: -x[1]["last_seen"]
        )[:5]
        if recent:
            text += "🕒 <b>Последние активные:</b>\n"
            for uid, o in recent:
                username = o.get("username") or str(uid)
                diff = now - o["last_seen"]
                if diff < 60:
                    ago = "только что"
                elif diff < 3600:
                    ago = str(diff // 60) + " мин назад"
                elif diff < 86400:
                    ago = str(diff // 3600) + " ч назад"
                else:
                    ago = str(diff // 86400) + " дн назад"
                text += "• " + username + " — " + ago + "\n"

    await update.message.reply_text(text, parse_mode="HTML")


# ============================================================
# КНОПКИ
# ============================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "copy_link":
        o = get_owner(user_id)
        bot_username = (await context.bot.get_me()).username
        link = "https://t.me/" + bot_username + "?start=" + o["code"]
        await query.message.reply_text(
            "📋 Твоя ссылка (нажми и удерживай, чтобы скопировать):\n\n"
            "<code>" + link + "</code>",
            parse_mode="HTML"
        )

    elif query.data == "my_stats":
        o = get_owner(user_id)
        await query.message.reply_text(
            "📊 Твоя статистика:\n\n"
            "📨 Получено анонимок: <b>" + str(o["messages_received"]) + "</b>",
            parse_mode="HTML"
        )

    elif query.data == "cancel_send":
        context.user_data.pop("sending_to", None)
        await query.edit_message_text("❌ Отправка отменена.")


# ============================================================
# ОБРАБОТКА СООБЩЕНИЙ
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import time
    user = update.effective_user

    if "sending_to" in context.user_data:
        owner_id = context.user_data["sending_to"]
        if owner_id == user.id:
            await update.message.reply_text("❌ Нельзя писать самому себе.")
            return
        try:
            if update.message.text:
                await context.bot.send_message(
                    chat_id=owner_id,
                    text="📨 <b>Анонимное сообщение:</b>\n\n" + update.message.text,
                    parse_mode="HTML"
                )
            elif update.message.photo:
                cap = "📷 <b>Анонимное фото</b>"
                if update.message.caption:
                    cap += "\n" + update.message.caption
                await context.bot.send_photo(chat_id=owner_id, photo=update.message.photo[-1].file_id, caption=cap, parse_mode="HTML")
            elif update.message.video:
                cap = "🎥 <b>Анонимное видео</b>"
                if update.message.caption:
                    cap += "\n" + update.message.caption
                await context.bot.send_video(chat_id=owner_id, video=update.message.video.file_id, caption=cap, parse_mode="HTML")
            elif update.message.voice:
                await context.bot.send_voice(chat_id=owner_id, voice=update.message.voice.file_id, caption="🎤 <b>Анонимное голосовое</b>", parse_mode="HTML")
            elif update.message.video_note:
                await context.bot.send_video_note(chat_id=owner_id, video_note=update.message.video_note.file_id)
            elif update.message.sticker:
                await context.bot.send_sticker(chat_id=owner_id, sticker=update.message.sticker.file_id)
            elif update.message.document:
                cap = "📎 <b>Анонимный файл</b>"
                if update.message.caption:
                    cap += "\n" + update.message.caption
                await context.bot.send_document(chat_id=owner_id, document=update.message.document.file_id, caption=cap, parse_mode="HTML")
            elif update.message.animation:
                await context.bot.send_animation(chat_id=owner_id, animation=update.message.animation.file_id, caption="🎞️ <b>Анонимная GIF</b>", parse_mode="HTML")
            else:
                await update.message.reply_text("❌ Такой тип сообщений не поддерживается.")
                return

            o = get_owner(owner_id)
            o["messages_received"] += 1
            o["last_seen"] = int(time.time())

            await update.message.reply_text(
                "✅ Сообщение отправлено анонимно!\n\n"
                "Можешь отправить ещё одно или закрыть бота."
            )
        except Exception as e:
            logging.error("Ошибка: " + str(e))
            await update.message.reply_text("❌ Не удалось отправить. Возможно, получатель заблокировал бота.")
        return

    await update.message.reply_text(
        "💬 Ты сейчас не отправляешь анонимку.\n\n"
        "Чтобы получить свою ссылку — /start"
    )


# ============================================================
# ЗАПУСК
# ============================================================
def main():
    if not BOT_TOKEN:
        print("❌ Нет токена!")
        return
    if ADMIN_ID == 0:
        print("⚠️ ВНИМАНИЕ: ADMIN_ID не указан! Команда /stats не будет работать.")
        print("Узнай свой ID через @userinfobot и вставь в код.")
    print("🚀 Бот анонимных вопросов запущен...")
    print("📊 Команда /stats доступна админу: " + str(ADMIN_ID))

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("my_link", my_link))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
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
