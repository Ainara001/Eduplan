from flask import Flask, request, render_template_string, send_file
from docxtpl import DocxTemplate

app = Flask(__name__)

@app.route("/")
def home():
    return "Это сервер Flask. Перейдите на /editor чтобы редактировать план."

@app.route("/editor")
def editor():
    return open("editor.html").read()

@app.route("/download", methods=["POST"])
def download():
    text = request.form.get("plan", "План пуст")
    doc = DocxTemplate("template.docx")
    doc.render({"plan": text})
    filename = "plan.docx"
    doc.save(filename)
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
