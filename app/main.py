import logging
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from app.services.bert_classify_service import BERTClassifyService
from app.services.bert_ner_service import BERTNERService
from app.services.ocr_service import OCRService
from app.utils.strukturkan_dokumen_lengkap import strukturkan_dokumen_lengkap
from core.config import settings

# --- Konfigurasi Aplikasi Flask ---

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = settings.UPLOAD_FOLDER
app.json.ensure_ascii = False

# Pastikan folder upload dan debug (dari settings) ada
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
if settings.DEBUG_FILE:  # Menggunakan settings yang diimpor
    os.makedirs(settings.DEBUG_FILE, exist_ok=True)

ocr_processor = OCRService(tesseract_cmd_path=settings.TESSERACT_PATH)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS


def save_uploaded_file(file) -> tuple[str, int] | tuple[str, None] | tuple[None, str]:
    """Save uploaded file to the upload folder."""
    if not file or file.filename == '':
        return "No file selected", 400

    if not allowed_file(file.filename):
        return "Unsupported file format, only : " + ", ".join(settings.ALLOWED_EXTENSIONS), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        file.save(file_path)
        logging.info(f"File saved: {file_path}")
        return file_path, None
    except Exception as e:
        logging.error(f"Failed to save file: {str(e)}")
        return None, "Failed to save file"


@app.route('/')
def home():
    return jsonify({"message": "Selamat datang di API OCR. Gunakan endpoint /ocr untuk ekstraksi teks."})


@app.route('/documents/ocr', methods=['POST'])
def ocr_endpoint():
    if 'file' not in request.files:
        logging.error("No file part in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    file_path, error = save_uploaded_file(file)

    try:

        extracted_text = ocr_processor.extract_text(file_path)  # Memanggil service

        if extracted_text.startswith(("[Error OCR:", "Gagal")) or \
                extracted_text.startswith("[Gagal pra-pemrosesan"):
            return jsonify({"error": extracted_text}), 500
        elif not extracted_text.strip() or extracted_text == "text_cleaned_mock":
            return jsonify({
                "message": "Tidak ada teks signifikan yang terdeteksi atau konten kosong setelah diproses.",
                "data": {
                    "text": extracted_text
                }
            }), 200
        else:
            return jsonify({
                "data": {
                    "text": extracted_text
                }
            }), 200
    except Exception as e:
        print(f"Error tak terduga di endpoint /ocr: {str(e)}")
        return jsonify({"error": f"Terjadi kesalahan internal server: {str(e)}"}), 500
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"File '{file_path}' berhasil dihapus (cleanup).")
            except OSError as e_remove:
                print(f"Gagal menghapus file '{file_path}' saat cleanup: {e_remove}")


@app.route('/documents/classify', methods=['POST'])
def classify_endpoint():
    if 'file' not in request.files:
        logging.error("No file part in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    file_path, error = save_uploaded_file(file)

    try:
        bert_classify_service = BERTClassifyService()

        extracted_text = ocr_processor.extract_text(file_path)  # Memanggil service
        predict = bert_classify_service.classify_text(extracted_text)

        if extracted_text.startswith(("[Error OCR:", "Gagal")) or \
                extracted_text.startswith("[Gagal pra-pemrosesan"):
            return jsonify({"error": extracted_text}), 500
        elif not extracted_text.strip() or extracted_text == "text_cleaned_mock":
            return jsonify({
                "message": "Tidak ada teks signifikan yang terdeteksi atau konten kosong setelah diproses.",
                "data": {
                    "text": extracted_text,
                    "predict": predict
                }
            }), 200
        else:
            return jsonify({
                "data": {
                    "type": predict[0]['label']
                }
            }), 200
    except Exception as e:
        print(f"Error tak terduga di endpoint /classify: {str(e)}")
        return jsonify({"error": f"Terjadi kesalahan internal server: {str(e)}"}), 500
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"File '{file_path}' berhasil dihapus (cleanup).")
            except OSError as e_remove:
                print(f"Gagal menghapus file '{file_path}' saat cleanup: {e_remove}")


@app.route('/documents/classify-extract', methods=['POST'])
def classify_extract_endpoint():
    if 'file' not in request.files:
        logging.error("No file part in request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    file_path, error = save_uploaded_file(file)

    try:
        bert_classify_service = BERTClassifyService()
        bert_ner_service = BERTNERService()

        extracted_text = ocr_processor.extract_text(file_path)  # Memanggil service
        predict = bert_classify_service.classify_text(extracted_text)
        extract = bert_ner_service.extract_text(extracted_text)

        if extracted_text.startswith(("[Error OCR:", "Gagal")) or \
                extracted_text.startswith("[Gagal pra-pemrosesan"):
            return jsonify({"error": extracted_text}), 500
        elif not extracted_text.strip() or extracted_text == "text_cleaned_mock":
            return jsonify({
                "message": "Tidak ada teks signifikan yang terdeteksi atau konten kosong setelah diproses.",
                "data": {
                    "text": extracted_text,
                    "predict": predict
                }
            }), 200
        else:
            data = strukturkan_dokumen_lengkap(
                ner_pipeline_output_list=extract,
                file_name_asli=file_path,
                teks_dokumen_asli=extracted_text,
                type=predict[0]['label']
            )
            return jsonify({
                # 'text': extracted_text,
                "data": data
            }), 200
    except Exception as e:
        print(f"Error tak terduga di endpoint /classify-extract: {str(e)}")
        return jsonify({"error": f"Terjadi kesalahan internal server: {str(e)}"}), 500
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"File '{file_path}' berhasil dihapus (cleanup).")
            except OSError as e_remove:
                print(f"Gagal menghapus file '{file_path}' saat cleanup: {e_remove}")
