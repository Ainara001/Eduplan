import base64
from urllib.parse import quote
import httpx
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from docxtpl import DocxTemplate

# === ТВОИ ДАННЫЕ ===
TOKEN = "8374010587:AAGuPA9SAOfh5YaCcmlopdszPAY6GTJWVrs"  # Telegram bot token
CF_API_TOKEN = "FtLRekpE8XxoSU7f7joPV8P1yw_eJiWPcakr48qQ"  # Cloudflare API Token
CF_ACCOUNT_ID = "40e01c9819d73953f76d02dbc3fd6ae5"  # Cloudflare Account ID
CF_MODEL = "@cf/meta/llama-3.1-8b-instruct"

CF_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_MODEL}"

# === PUBLIC URL для WebApp ===
WEBAPP_BASE_URL = "https://eduplan011-cgldrni99-ainaras-projects-bc848d65.vercel.app/editor.html"




# Для хранения данных пользователя
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
    user_id = update.message.from_user.id
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

        # base64 + urlquote для WebApp
        encoded = base64.urlsafe_b64encode(plan.encode("utf-8")).decode("ascii")
        encoded_quoted = quote(encoded, safe='')

        if WEBAPP_BASE_URL == "https://YOUR_DEPLOYED_WEBAPP_URL/edit":
            # если не настроен WEBAPP_BASE_URL
            await update.message.reply_text(
                "⚠️ WEBAPP_BASE_URL не настроен. Открой bot.py и установи WEBAPP_BASE_URL на URL, "
                "куда ты задеплоил editor.html (обязательно HTTPS)."
            )
            # сразу отправляем docx
            doc = DocxTemplate("template.docx")
            context_data = {
                "topic": user_data[user_id]["topic"],
                "class": user_data[user_id]["class"],
                "date": user_data[user_id]["date"],
                "teacher": user_data[user_id]["teacher"],
                "plan": plan
            }
            doc.render(context_data)
            filename = f"plan_{user_id}.docx"
            doc.save(filename)
            await update.message.reply_document(open(filename, "rb"))
            del user_data[user_id]
            return

        webapp_url = f"{WEBAPP_BASE_URL}?plan={encoded_quoted}"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Открыть редактор плана", web_app=WebAppInfo(url=webapp_url))
        ]])

        await update.message.reply_text(
            "План сгенерирован. Нажмите кнопку, чтобы открыть редактор и при необходимости изменить текст. "
            "После редактирования нажмите 'Скачать' — бот пришлёт DOCX.",
            reply_markup=keyboard
        )

# ----------------------
# WEBAPP DATA HANDLER
# ----------------------
async def webapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.web_app_data.data
    user_id = update.message.from_user.id
    plan_text = raw
    try:
        import json
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "text" in parsed:
            plan_text = parsed["text"]
    except Exception:
        pass

    doc = DocxTemplate("template.docx")
    ud = user_data.get(user_id, {})
    context_data = {
        "topic": ud.get("topic", ""),
        "class": ud.get("class", ""),
        "date": ud.get("date", ""),
        "teacher": ud.get("teacher", ""),
        "plan": plan_text
    }
    doc.render(context_data)
    filename = f"plan_{user_id}.docx"
    doc.save(filename)
    await update.message.reply_document(open(filename, "rb"))

    if user_id in user_data:
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
