from flask import Flask, render_template, request, send_file
from docxtpl import DocxTemplate
import os

app = Flask(__name__)

# временное хранилище текстов планов
plans = {}

@app.route('/edit/<user_id>', methods=['GET', 'POST'])
def edit_plan(user_id):
    if request.method == 'POST':
        plan_text = request.form['plan']
        # сохраняем на сервере (для возможного повторного редактирования)
        plans[user_id] = plan_text

        # создаем DOCX
        doc = DocxTemplate("template.docx")
        doc.render({"plan": plan_text})
        filename = f"plan_{user_id}.docx"
        doc.save(filename)

        # возвращаем ссылку на скачивание
        return f'Файл сохранён. <a href="/download/{filename}">Скачать DOCX</a>'

    # GET — показываем форму для редактирования
    plan_text = plans.get(user_id, "")
    return render_template("editor.html", plan=plan_text)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
