import logging
import os
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8837183643:AAGivwNcHn0XlGkHKSnS8kNXqboA6fVga3M")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ============================================================
# ХРАНИЛИЩЕ В ПАМЯТИ
# ============================================================
# user_id -> {"link_code": "...", "partner_id": None, "partner_code": None}
users = {}
# code -> owner_user_id
codes = {}


def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "link_code": secrets.token_urlsafe(8),
            "partner_id": None,
            "partner_code": None,
            "username": None,
            "first_name": None,
        }
        codes[users[user_id]["link_code"]] = user_id
    return users[user_id]


def get_bot_username(app):
    return app.bot.username


# ============================================================
# КОМАНДЫ
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)
    u["username"] = user.username
    u["first_name"] = user.first_name

    # Если перешли по ссылке (deep link)
    if context.args:
        code = context.args[0]
        # Это ссылка владельца
        if code in codes and codes[code] != user.id:
            owner_id = codes[code]
            owner = get_user(owner_id)
            # Проверка: у владельца уже есть партнёр?
            if owner["partner_id"] is not None and owner["partner_id"] != user.id:
                await update.message.reply_text(
                    "❌ У этого пользователя уже есть активный диалог.\n"
                    "Попроси его завершить текущий чат."
                )
                return
            # Связываем
            owner["partner_id"] = user.id
            u["partner_id"] = owner_id
            owner["partner_code"] = u["link_code"]
            u["partner_code"] = code
            # Уведомляем обоих
            try:
                await context.bot.send_message(
                    chat_id=owner_id,
                    text="🔔 Кто-то перешёл по твоей ссылке!\n\nТеперь вы можете общаться анонимно. Просто пиши сюда сообщения."
                )
            except:
                pass
            await update.message.reply_text(
                "✅ Ты подключён к анонимному чату!\n\n"
                "Просто пиши сообщения — они полетят анонимно.\n"
                "Тебе ответят — ты увидишь ответ здесь.\n\n"
                "Чтобы выйти — /stop"
            )
            return
        else:
            await update.message.reply_text(
                "❌ Ссылка недействительна или устарела."
            )
            return

    # Обычный старт
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={u['link_code']}"

    if u["partner_id"]:
        text = (
            "💬 Ты в анонимном чате.\n\n"
            "Просто пиши сообщения — они летят партнёру анонимно.\n\n"
            "Выйти: /stop\n"
            "Узнать свою ссылку: /my_link"
        )
    else:
        text = (
            "👋 Привет! Я бот для анонимного чата.\n\n"
            "**Как пользоваться:**\n"
            "1️⃣ Скопируй свою ссылку ниже\n"
            "2️⃣ Отправь её другу (или кому хочешь)\n"
            "3️⃣ Когда он перейдёт — начнётся анонимный чат\n"
            "4️⃣ Пишите друг другу — никто не узнает, кто вы\n\n"
            f"🔗 **Твоя ссылка:**\n`{link}`\n\n"
            "Скопируй её и отправь кому надо."
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def my_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={u['link_code']}"
    await update.message.reply_text(
        f"🔗 **Твоя ссылка для анонимного чата:**\n\n`{link}`\n\n"
        f"Отправь её другу — и начнётся анонимный диалог.",
        parse_mode="Markdown"
    )


async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)
    partner_id = u["partner_id"]
    if not partner_id:
        await update.message.reply_text("❌ Ты не в чате ни с кем.")
        return
    partner = get_user(partner_id)
    u["partner_id"] = None
    u["partner_code"] = None
    if partner:
        partner["partner_id"] = None
        partner["partner_code"] = None
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text="🔌 Собеседник вышел из чата.\n\nХочешь начать новый — /my_link"
            )
        except:
            pass
    await update.message.reply_text(
        "✅ Ты вышел из чата.\n\n"
        "Хочешь начать новый — /start или /my_link"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **Помощь**\n\n"
        "/start — начать, получить ссылку\n"
        "/my_link — показать твою ссылку\n"
        "/stop — выйти из чата\n\n"
        "**Как работает:**\n"
        "Ты отправляешь ссылку другу. Он переходит. Вы общаетесь анонимно — "
        "ни ты, ни он не видите имён и username друг друга.",
        parse_mode="Markdown"
    )


# ============================================================
# ПЕРЕСЫЛКА СООБЩЕНИЙ
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)
    u["username"] = user.username
    u["first_name"] = user.first_name

    # Если не в чате
    if not u["partner_id"]:
        await update.message.reply_text(
            "💬 Ты пока не в чате.\n\n"
            "Нажми /start чтобы получить ссылку, или /my_link чтобы посмотреть свою."
        )
        return

    partner_id = u["partner_id"]

    # Пересылаем сообщение партнёру
    try:
        # Текст
        if update.message.text:
            await context.bot.send_message(
                chat_id=partner_id,
                text=f"💬 {update.message.text}"
            )
        # Фото
        elif update.message.photo:
            await context.bot.send_photo(
                chat_id=partner_id,
                photo=update.message.photo[-1].file_id,
                caption="📷 Фото" + (f"\n{update.message.caption}" if update.message.caption else "")
            )
        # Видео
        elif update.message.video:
            await context.bot.send_video(
                chat_id=partner_id,
                video=update.message.video.file_id,
                caption="🎥 Видео" + (f"\n{update.message.caption}" if update.message.caption else "")
            )
        # Голосовое
        elif update.message.voice:
            await context.bot.send_voice(
                chat_id=partner_id,
                voice=update.message.voice.file_id,
                caption="🎤 Голосовое"
            )
        # Стикер
        elif update.message.sticker:
            await context.bot.send_sticker(
                chat_id=partner_id,
                sticker=update.message.sticker.file_id
            )
        # Документ
        elif update.message.document:
            await context.bot.send_document(
                chat_id=partner_id,
                document=update.message.document.file_id,
                caption="📎 Файл" + (f"\n{update.message.caption}" if update.message.caption else "")
            )
        else:
            await update.message.reply_text("❌ Такой тип сообщений не поддерживается.")
    except Exception as e:
        logging.error(f"Ошибка пересылки: {e}")
        await update.message.reply_text(
            "❌ Не удалось отправить. Собеседник мог заблокировать бота."
        )


# ============================================================
# ЗАПУСК
# ============================================================

def main():
    if not BOT_TOKEN or BOT_TOKEN == "СЮДА_ВСТАВЬ_СВОЙ_ТОКЕН":
        print("❌ Нет токена!")
        return
    print("🚀 Анонимный бот запущен...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("my_link", my_link))
    app.add_handler(CommandHandler("stop", stop_chat))
    app.add_handler(MessageHandler(~filters.COMMAND & (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VOICE | filters.Sticker.ALL | filters.Document.ALL), handle_message))
    print("✅ Готов!")
    app.run_polling()


if __name__ == "__main__":
    main()
