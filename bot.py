import base64
from urllib.parse import quote
import httpx
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from docxtpl import DocxTemplate

# === ТВОИ ДАННЫЕ ===
TOKEN = "8374010587:AAGuPA9SAOfh5YaCcmlopdszPAY6GTJWVrs"  # Telegram bot token
CF_API_TOKEN = "FtLRekpE8XxoSU7f7joPV8P1yw_eJiWPcakr48qQ"  # Cloudflare API Token
CF_ACCOUNT_ID = "40e01c9819d73953f76d02dbc3fd6ae5"  # Cloudflare Account ID
CF_MODEL = "@cf/meta/llama-3.1-8b-instruct"

CF_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_MODEL}"

# === URL для Flask редактора ===
# если локально: http://127.0.0.1:5000/edit
# если на сервере/хостинге — публичный адрес
FLASK_BASE_URL = "http://127.0.0.1:5000/edit"

# Для хранения данных пользователя в боте
user_data = {}
plans = {}  # для Flask

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
        await update.message.reply_text("Генерирую поурочный план...")

        # ------ PROMPT ------
        prompt = f"""
Сгенерируй поурочный план.
Тема: {user_data[user_id]["topic"]}
Класс: {user_data[user_id]["class"]}
Дата: {user_data[user_id]["date"]}
Учитель: {user_data[user_id]["teacher"]}

Нужные блоки:
1. Цели урока
2. Оборудование и материалы
3. Ход урока (этапы, время)
4. Формы оценивания
5. Домашнее задание
"""

        # ----------------------
        # Cloudflare AI REQUEST через httpx
        # ----------------------
        headers = {
            "Authorization": f"Bearer {CF_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"prompt": prompt, "max_tokens": 900}

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(CF_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                plan = data.get("result", {}).get("response", "")
        except Exception as e:
            plan = f"(Ошибка при запросе к Cloudflare: {e})"

        # сохраняем план
        user_data[user_id]["plan"] = plan
        plans[user_id] = plan  # для Flask

        # генерируем кнопку для редактирования
        edit_url = f"{FLASK_BASE_URL}/{user_id}"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Открыть редактор плана", url=edit_url)
        ]])

        await update.message.reply_text(
            "План сгенерирован. Нажмите кнопку, чтобы открыть редактор и при необходимости изменить текст. "
            "После редактирования нажмите 'Скачать' — бот пришлёт DOCX.",
            reply_markup=keyboard
        )

# ----------------------
# RUN BOT
# ----------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))
    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
