import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

# ============================================================
# ТОКЕН — берётся из Railway (переменная BOT_TOKEN)
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8837183643:AAGivwNcHn0XlGkHKSnS8kNXqboA6fVga3M")

# Языки для кнопок
POPULAR_LANGS = {
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en",
    "🇩🇪 Deutsch": "de",
    "🇫🇷 Français": "fr",
    "🇪🇸 Español": "es",
    "🇮🇹 Italiano": "it",
    "🇵🇹 Português": "pt",
    "🇹🇷 Türkçe": "tr",
    "🇨🇳 中文": "zh-CN",
    "🇯🇵 日本語": "ja",
    "🇰🇷 한국어": "ko",
    "🇸🇦 العربية": "ar",
    "🇮🇳 हिन्दी": "hi",
    "🇺🇦 Українська": "uk",
    "🇰🇿 Қазақша": "kk",
    "🇵🇱 Polski": "pl",
}

user_langs = {}
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    text = (
        f"👋 Привет, {name}!\n\n"
        "🌍 Я бот-переводчик на 100+ языков.\n\n"
        "1️⃣ Выбери язык кнопкой\n"
        "2️⃣ Отправь текст\n"
        "3️⃣ Получи перевод!\n\n"
        "/help — помощь"
    )
    await update.message.reply_text(text, reply_markup=build_lang_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **Помощь**\n\n"
        "/lang — сменить язык перевода\n"
        "/langs — список языков\n"
        "Просто отправь текст — переведу!\n\n"
        "💡 Можно переслать чужое сообщение.",
        parse_mode="Markdown"
    )


async def langs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌍 Выбери язык:", reply_markup=build_lang_keyboard())


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        code = context.args[0].lower()
        user_langs[update.effective_user.id] = code
        await update.message.reply_text(f"✅ Язык изменён на: {code}")
        return
    await update.message.reply_text("🌍 Выбери язык:", reply_markup=build_lang_keyboard())


def build_lang_keyboard():
    keyboard = []
    row = []
    for name, code in POPULAR_LANGS.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang:{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


async def lang_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.split(":")[1]
    user_langs[query.from_user.id] = code
    await query.edit_message_text(f"✅ Язык: {code}\n\nОтправь текст!")


async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
    if len(text) > 4000:
        await update.message.reply_text("❌ Текст слишком длинный (макс. 4000)")
        return
    target = user_langs.get(update.effective_user.id, "ru")
    try:
        translated = GoogleTranslator(source='auto', target=target).translate(text)
        if not translated:
            await update.message.reply_text("❌ Не удалось перевести")
            return
        if translated.strip().lower() == text.strip().lower():
            await update.message.reply_text("ℹ️ Текст уже на этом языке")
            return
        await update.message.reply_text(f"🌍 **Перевод:**\n\n{translated}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка. Попробуй позже")


def main():
    if not BOT_TOKEN or BOT_TOKEN == "СЮДА_ВСТАВЬ_СВОЙ_ТОКЕН":
        print("❌ Нет токена! Добавь BOT_TOKEN в Railway Variables.")
        return
    print("🚀 Бот запущен...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("langs", langs_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CallbackQueryHandler(lang_button, pattern="^lang:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))
    print("✅ Готов!")
    app.run_polling()


if __name__ == "__main__":
    main()
