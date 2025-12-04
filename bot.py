import base64
import json
import os
from urllib.parse import quote, unquote

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from docxtpl import DocxTemplate
from docx import Document

TOKEN = "8374010587:AAGuPA9SAOfh5YaCcmlopdszPAY6GTJWVrs"

WEBAPP_BASE_URL = "https://твоя_вёрсел_ссылка/editor.html"

user_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите тему урока:")


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

        plan_text = (
            f"Тема: {user_data[user_id]['topic']}\n"
            f"Класс: {user_data[user_id]['class']}\n"
            f"Дата: {user_data[user_id]['date']}\n"
            f"Учитель: {user_data[user_id]['teacher']}\n\n"
            f"Введите здесь текст плана урока..."
        )

        user_data[user_id]["plan"] = plan_text

        encoded = quote(base64.b64encode(plan_text.encode("utf-8")))
        webapp_url = f"{WEBAPP_BASE_URL}?plan={encoded}"

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Открыть редактор плана", web_app=WebAppInfo(url=webapp_url))
        ]])

        await update.message.reply_text(
            "Нажмите кнопку, чтобы открыть редактор прямо в Telegram.",
            reply_markup=keyboard
        )


async def webapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    raw = update.message.web_app_data.data

    # Проверка: пришли ли данные о редактировании Word (кнопка "Редактировать документ")
    if raw.startswith("{") and "\"text\"" in raw:
        try:
            data = json.loads(raw)
            new_text = data.get("text", "")
        except:
            new_text = raw

        # Генерируем новый docx после редактирования
        new_doc = DocxTemplate("template.docx")
        new_doc.render({
            "topic": user_data[user_id].get("topic", ""),
            "class": user_data[user_id].get("class", ""),
            "date": user_data[user_id].get("date", ""),
            "teacher": user_data[user_id].get("teacher", ""),
            "plan": new_text
        })

        new_filename = f"updated_{user_id}.docx"
        new_doc.save(new_filename)

        await update.message.reply_document(open(new_filename, "rb"))
        return

    # --------------------
    # ТВОЯ СТАРАЯ ЛОГИКА
    # --------------------

    try:
        data = json.loads(raw)
        plan_text = data.get("text", "")
    except Exception:
        plan_text = raw

    user_data[user_id]["plan"] = plan_text

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

    # Отправка документа — СТАРАЯ логика
    await update.message.reply_document(open(filename, "rb"))

    # ---------------------------------------
    # НОВАЯ ЛОГИКА: кнопка "Редактировать документ"
    # ---------------------------------------

    # Загружаем текст из созданного Word
    doc_loaded = Document(filename)
    full_text = "\n".join([p.text for p in doc_loaded.paragraphs])

    encoded_text = quote(base64.b64encode(full_text.encode("utf-8")))
    edit_url = f"{WEBAPP_BASE_URL}?edit={encoded_text}"

    edit_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Редактировать документ", web_app=WebAppInfo(url=edit_url))
    ]])

    await update.message.reply_text(
        "Хотите изменить документ? Нажмите кнопку.",
        reply_markup=edit_keyboard
    )

    # Удаляем temporary данные
    del user_data[user_id]


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.StatusUpdate.WEB_APP_DATA, text_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_handler))

    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
