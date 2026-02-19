from flask import Flask, render_template, request, send_file
import requests
from langdetect import detect
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
import os

app = Flask(__name__)

languages = {
    "Auto Detect": "auto",
    "English": "en",
    "Hindi": "hi",
    "Gujarati": "gu",
    "Marathi": "mr",
    "Tamil": "ta",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Portuguese": "pt"
}

MYMEMORY_EMAIL = "your_email@gmail.com"

def auto_detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

def translate_text(text, source_lang, target_lang):
    source_code = auto_detect_language(text) if source_lang == "Auto Detect" else languages[source_lang]
    target_code = languages[target_lang]

    url = "https://api.mymemory.translated.net/get"
    params = {"q": text, "langpair": f"{source_code}|{target_code}", "de": MYMEMORY_EMAIL}

    response = requests.get(url, params=params).json()
    translated = response["responseData"]["translatedText"]

    if "MYMEMORY WARNING" in translated.upper():
        return "⚠ Daily translation limit reached. Try later."

    return translated



def correct_grammar(text):
    lines = text.split("\n")
    corrected_lines = []

    url = "https://api.languagetool.org/v2/check"

    for line in lines:
        if not line.strip():
            corrected_lines.append("")
            continue

        data = {"text": line, "language": "auto"}
        response = requests.post(url, data=data).json()

        for match in reversed(response["matches"]):
            if match["replacements"]:
                r = match["replacements"][0]["value"]
                o = match["offset"]
                l = match["length"]
                line = line[:o] + r + line[o+l:]

        corrected_lines.append(line)

    return "\n".join(corrected_lines)

@app.route("/", methods=["GET", "POST"])
def index():
    translated_text = ""
    original_text = ""
    selected_source = "Auto Detect"
    selected_target = "English"

    if request.method == "POST":
        original_text = request.form["text"]
        selected_source = request.form["source"]
        selected_target = request.form["target"]

        if original_text.strip():
            translated_text = translate_text(original_text, selected_source, selected_target)
            if not translated_text.startswith("⚠"):
                translated_text = correct_grammar(translated_text)

    return render_template(
        "index.html",
        translated=translated_text,
        original_text=original_text,
        languages=languages.keys(),
        selected_source=selected_source,
        selected_target=selected_target
    )


@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    translated_text = request.form.get("translated_text", "")
    if not translated_text.strip():
        return "No translated text to download."

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    # Windows system font paths
    hindi_font_path = r"C:\Windows\Fonts\Mangal.ttf"
    gujarati_font_path = r"C:\Windows\Fonts\Shruti.ttf"

    text_style = styles['BodyText']  # default fallback

    # Detect script and load appropriate font
    if any('\u0900' <= ch <= '\u097F' for ch in translated_text) and os.path.exists(hindi_font_path):
        pdfmetrics.registerFont(TTFont("HindiFont", hindi_font_path))
        styles.add(ParagraphStyle(name='HindiStyle', fontName='HindiFont', fontSize=12, leading=15))
        text_style = styles['HindiStyle']

    elif any('\u0A80' <= ch <= '\u0AFF' for ch in translated_text) and os.path.exists(gujarati_font_path):
        pdfmetrics.registerFont(TTFont("GujaratiFont", gujarati_font_path))
        styles.add(ParagraphStyle(name='GujaratiStyle', fontName='GujaratiFont', fontSize=12, leading=15))
        text_style = styles['GujaratiStyle']

    story = []
    story.append(Paragraph("Translated Text", styles['Title']))
    story.append(Spacer(1, 12))

    formatted_text = translated_text.replace("\n", "<br/>")
    story.append(Paragraph(formatted_text, text_style))

    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="translation.pdf", mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
