import logging
import os
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8837183643:AAGZXuqL6CmB_uj1yVPqvpM5lx7duDzTheg")

# ТВОЙ КАНАЛ (если нужно — оставь, если нет — удали блок с MY_CHANNEL)
MY_CHANNEL = "@SenTygames"
MY_CHANNEL_LINK = "https://t.me/SenTygames"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

codes = {}
owners = {}


def get_owner(user_id):
    if user_id not in owners:
        code = secrets.token_urlsafe(4)
        owners[user_id] = {"code": code, "messages_received": 0}
        codes[code] = user_id
    return owners[user_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    bot_username = (await context.bot.get_me()).username
    link = "https://t.me/" + bot_username + "?start=" + o["code"]

    # КРАСИВОЕ СООБЩЕНИЕ как в @voprosy
    text = (
        "👋 <b>Привет!</b>\n\n"
        "Начни получать анонимные вопросы прямо сейчас 👀\n\n"
        "🔗 <b>Ссылка для получения анонимных вопросов:</b>\n"
        "<code>" + link + "</code>\n\n"
        "Размести эту ссылку 👆 в описании профиля ✈️ / TikTok / Instagram, "
        "чтобы тебе могли написать."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Скопировать ссылку", callback_data="copy_link")],
        [InlineKeyboardButton("📤 Поделиться ссылкой", callback_data="share_link")],
        [InlineKeyboardButton("👥 Добавить бота в чат", url="https://t.me/" + bot_username + "?startgroup=true")],
    ])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)


async def my_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    o = get_owner(user.id)
    bot_username = (await context.bot.get_me()).username
    link = "https://t.me/" + bot_username + "?start=" + o["code"]

    text = (
        "🔗 <b>Твоя ссылка:</b>\n\n"
        "<code>" + link + "</code>\n\n"
        "📊 Получено сообщений: <b>" + str(o["messages_received"]) + "</b>"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Скопировать ссылку", callback_data="copy_link")],
        [InlineKeyboardButton("📤 Поделиться ссылкой", callback_data="share_link")],
    ])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Помощь</b>\n\n"
        "/start — показать твою ссылку\n"
        "/my_link — снова показать ссылку + статистику\n"
        "/help — эта справка\n\n"
        "<b>Как пользоваться:</b>\n"
        "1. Получи ссылку через /start\n"
        "2. Опубликуй её где угодно\n"
        "3. Тебе будут писать анонимно\n"
        "4. Ты не узнаешь, кто именно написал",
        parse_mode="HTML"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "copy_link":
        user_id = query.from_user.id
        o = get_owner(user_id)
        bot_username = (await context.bot.get_me()).username
        link = "https://t.me/" + bot_username + "?start=" + o["code"]
        await query.message.reply_text(
            "📋 <b>Твоя ссылка (нажми и удерживай, чтобы скопировать):</b>\n\n"
            "<code>" + link + "</code>",
            parse_mode="HTML"
        )

    elif query.data == "share_link":
        user_id = query.from_user.id
        o = get_owner(user_id)
        bot_username = (await context.bot.get_me()).username
        link = "https://t.me/" + bot_username + "?start=" + o["code"]
        share_url = "https://t.me/share/url?url=" + link + "&text=Задай мне анонимный вопрос!"
        await query.message.reply_text(
            "📤 <b>Поделись ссылкой:</b>\n\n"
            "Нажми кнопку ниже — откроется список чатов, куда можно отправить ссылку.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📤 Поделиться", url=share_url)
            ]])
        )

    elif query.data == "cancel_send":
        context.user_data.pop("sending_to", None)
        await query.edit_message_text("❌ Отправка отменена.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                    cap = cap + "\n" + update.message.caption
                await context.bot.send_photo(
                    chat_id=owner_id,
                    photo=update.message.photo[-1].file_id,
                    caption=cap,
                    parse_mode="HTML"
                )
            elif update.message.video:
                cap = "🎥 <b>Анонимное видео</b>"
                if update.message.caption:
                    cap = cap + "\n" + update.message.caption
                await context.bot.send_video(
                    chat_id=owner_id,
                    video=update.message.video.file_id,
                    caption=cap,
                    parse_mode="HTML"
                )
            elif update.message.voice:
                await context.bot.send_voice(
                    chat_id=owner_id,
                    voice=update.message.voice.file_id,
                    caption="🎤 <b>Анонимное голосовое</b>",
                    parse_mode="HTML"
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
                cap = "📎 <b>Анонимный файл</b>"
                if update.message.caption:
                    cap = cap + "\n" + update.message.caption
                await context.bot.send_document(
                    chat_id=owner_id,
                    document=update.message.document.file_id,
                    caption=cap,
                    parse_mode="HTML"
                )
            elif update.message.animation:
                await context.bot.send_animation(
                    chat_id=owner_id,
                    animation=update.message.animation.file_id,
                    caption="🎞️ <b>Анонимная GIF</b>",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ Такой тип сообщений не поддерживается.")
                return

            o = get_owner(owner_id)
            o["messages_received"] = o["messages_received"] + 1
            await update.message.reply_text(
                "✅ <b>Сообщение отправлено анонимно!</b>\n\n"
                "Можешь отправить ещё одно или закрыть бота.",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error("Ошибка: " + str(e))
            await update.message.reply_text(
                "❌ Не удалось отправить. Возможно, получатель заблокировал бота."
            )
        return

    await update.message.reply_text(
        "💬 Ты сейчас не отправляешь анонимку.\n\n"
        "Чтобы получить свою ссылку — /start"
    )


def main():
    if not BOT_TOKEN:
        print("Нет токена!")
        return
    print("Бот запущен...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("my_link", my_link))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        ~filters.COMMAND & (
            filters.TEXT | filters.PHOTO | filters.VIDEO |
            filters.VOICE | filters.VIDEO_NOTE | filters.Sticker.ALL |
            filters.Document.ALL | filters.ANIMATION
        ),
        handle_message
    ))

    print("Готов!")
    app.run_polling()


if __name__ == "__main__":
    main()
