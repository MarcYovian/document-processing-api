import logging
import os

from flask import Blueprint, request, jsonify

from ..services.classifier_service import TextClassifierService, ClassifierError
from ..services.ocr_service import OCRService, TesseractNotFoundError, OCRError
from ..utils.file_handler import save_uploaded_file

logger = logging.getLogger(__name__)
classifier_bp = Blueprint('classifier_bp', __name__)

ocr_service: OCRService = None
classifier_service: TextClassifierService = None


def init_classifier_services(ocr_svc_instance: OCRService, classifier_svc_instance: TextClassifierService):
    """Fungsi helper untuk menerima instance service yang sudah dibuat."""
    global ocr_service, classifier_service
    ocr_service = ocr_svc_instance
    classifier_service = classifier_svc_instance


@classifier_bp.route('/classify', methods=['POST'])
def classify_document_endpoint():
    """
    Endpoint untuk mengunggah file, melakukan OCR, lalu mengklasifikasikan teksnya.
    """
    if ocr_service is None or classifier_service is None:
        logger.error("Satu atau lebih service belum diinisialisasi.")
        return jsonify({"error": "Layanan tidak tersedia saat ini."}), 503

    if 'file' not in request.files:
        return jsonify({"error": "Request harus menyertakan bagian 'file'."}), 400

    file = request.files['file']
    file_path, error = save_uploaded_file(file)
    if error:
        return jsonify({"error": error}), 500

    try:
        logger.info(f"Memulai pipeline OCR untuk file: {file.filename}")
        ocr_result = ocr_service.extract_text_from_file(file_path)

        text_to_classify = ocr_result.get("text_for_classification")

        logger.info("Memulai klasifikasi pada teks hasil OCR...")
        classification_result = classifier_service.classify_text(text_to_classify)

        return jsonify({
            'data': {
                "classification": classification_result,
                "text_preview": text_to_classify[:200] + "...",
                "file_name": ocr_result.get("file_name"),
            }
        }), 200
    except OCRError as e:
        logger.error(f"Terjadi error OCR yang terkendali: {e}", exc_info=True)
        return jsonify({"error": f"Gagal saat ekstraksi teks: {e}"}), 500
    except ClassifierError as e:
        logger.error(f"Terjadi error klasifikasi yang terkendali: {e}", exc_info=True)
        return jsonify({"error": f"Gagal saat klasifikasi teks: {e}"}), 500

    except Exception as e:
        logger.critical(f"Terjadi error internal server yang tidak terduga: {e}", exc_info=True)
        return jsonify({"error": "Terjadi kesalahan internal pada server."}), 500
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"File sementara berhasil dihapus: {file_path}")
            except OSError as e:
                logger.error(f"Gagal menghapus file sementara: {file_path}. Error: {e}")