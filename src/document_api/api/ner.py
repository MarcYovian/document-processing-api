import logging
import os

import numpy as np
from flask import Blueprint, request, jsonify

from ..services.ner_service import NERService, NERError
from ..services.ocr_service import OCRService, OCRError
from ..utils.file_handler import save_uploaded_file

logger = logging.getLogger(__name__)
ner_bp = Blueprint('ner_bp', __name__)

ocr_service: OCRService = None
ner_service: NERService = None


def init_ner_services(ocr_svc_instance: OCRService,
                      ner_svc_instance: NERService):
    """Fungsi helper untuk menerima instance service yang sudah dibuat."""
    global ocr_service, ner_service
    ocr_service = ocr_svc_instance
    ner_service = ner_svc_instance


def sanitize_for_json(data):
    """
    Mengubah tipe data NumPy yang tidak bisa di-serialize menjadi tipe data Python standar.
    """
    if isinstance(data, (np.int_, np.intc, np.intp, np.int8,
                         np.int16, np.int32, np.int64, np.uint8,
                         np.uint16, np.uint32, np.uint64)):
        return int(data)
    elif isinstance(data, (np.float16, np.float32, np.float64)):
        return float(data)
    elif isinstance(data, (np.ndarray,)):
        return data.tolist()
    elif isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(v) for v in data]
    return data


@ner_bp.route('extract-entities', methods=['POST'])
def extract_entities_endpoint():
    """
    Endpoint untuk mengunggah file, melakukan OCR, lalu mengekstrak entitas dari teksnya.
    """
    if ocr_service is None or ner_service is None:
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

        text_for_ner = ocr_result.get("text_for_ner")

        logger.info("Memulai ekstraksi entitas pada teks hasil OCR...")
        entities = ner_service.predict_entities_text(text_for_ner)

        sanitized_entities = sanitize_for_json(entities)

        # Format respons JSON
        return jsonify({
            'data': {
                "file_name": ocr_result.get("file_name"),
                "entities": sanitized_entities
            }
        }), 200

    except OCRError as e:
        logger.error(f"Terjadi error OCR: {e}", exc_info=True)
        return jsonify({"error": f"Gagal saat ekstraksi teks: {e}"}), 500
    except NERError as e:
        logger.error(f"Terjadi error NER: {e}", exc_info=True)
        return jsonify({"error": f"Gagal saat ekstraksi entitas: {e}"}), 500
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
