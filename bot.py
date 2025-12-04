import base64
import json
from urllib.parse import quote, unquote
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from docxtpl import DocxTemplate

# === ТВОИ ДАННЫЕ ===
TOKEN = "8374010587:AAGuPA9SAOfh5YaCcmlopdszPAY6GTJWVrs"

# URL твоего Web App (должен быть HTTPS, например Vercel)
WEBAPP_BASE_URL = "https://твоя_вёрсел_ссылка/editor.html"

# Храним данные пользователей
user_data = {}

# ----------------------
# START COMMAND
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите тему урока:")

# ----------------------
# TEXT HANDLER
# ----------------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if user_id not in user_data:
        user_data[user_id] = {"topic": text}
        await update.message.reply_text("Введите класс/группу:")
        return
    if "class" not in user_data[user_id]:
        user_data[user_id]["class"] = text
        await update.message.reply_text("Введите дату урока:")
        return
    if "date" not in user_data[user_id]:
        user_data[user_id]["date"] = text
        await update.message.reply_text("Введите ФИО преподавателя:")
        return
    if "teacher" not in user_data[user_id]:
        user_data[user_id]["teacher"] = text

        # Сохраняем план (пока просто текст для редактора)
        plan_text = f"Тема: {user_data[user_id]['topic']}\nКласс: {user_data[user_id]['class']}\nДата: {user_data[user_id]['date']}\nУчитель: {user_data[user_id]['teacher']}\n\nВведите здесь текст плана урока..."
        user_data[user_id]["plan"] = plan_text

        # Кодируем текст для передачи в Web App
        encoded = quote(base64.b64encode(plan_text.encode("utf-8")))

        webapp_url = f"{WEBAPP_BASE_URL}?plan={encoded}"

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Открыть редактор плана", web_app=WebAppInfo(url=webapp_url))
        ]])

        await update.message.reply_text(
            "Нажмите кнопку, чтобы открыть редактор прямо в Telegram.",
            reply_markup=keyboard
        )

# ----------------------
# WEBAPP DATA HANDLER
# ----------------------
async def webapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    raw = update.message.web_app_data.data

    try:
        data = json.loads(raw)
        plan_text = data.get("text", "")
    except Exception:
        plan_text = raw

    # Сохраняем план
    user_data[user_id]["plan"] = plan_text

    # Создаём DOCX
    doc = DocxTemplate("template.docx")
    context_data = {
        "topic": user_data[user_id]["topic"],
        "class": user_data[user_id]["class"],
        "date": user_data[user_id]["date"],
        "teacher": user_data[user_id]["teacher"],
        "plan": plan_text
    }
    doc.render(context_data)
    filename = f"plan_{user_id}.docx"
    doc.save(filename)

    # Отправляем пользователю
    await update.message.reply_document(open(filename, "rb"))

    # Удаляем данные
    del user_data[user_id]

# ----------------------
# RUN BOT
# ----------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.StatusUpdate.WEB_APP_DATA, text_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_handler))
    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
