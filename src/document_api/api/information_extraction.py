import logging
import os

import numpy as np
from flask import Blueprint, request, jsonify

from ..services.classifier_service import TextClassifierService
from ..services.information_extraction_service import InformationExtractionService
from ..services.ner_service import NERService, NERError
from ..services.ocr_service import OCRService, OCRError
from ..utils.file_handler import save_uploaded_file

logger = logging.getLogger(__name__)
information_bp = Blueprint('information_bp', __name__)

ocr_service: OCRService = None
classifier_service: TextClassifierService = None
ner_service: NERService = None
info_extraction_service: InformationExtractionService = None


def init_information_services(ocr_svc_instance: OCRService,
                              classifier_svc_instance: TextClassifierService,
                              ner_svc_instance: NERService,
                              info_ext_svc_instance: InformationExtractionService):
    """Fungsi helper untuk menerima instance service yang sudah dibuat."""
    global ocr_service, classifier_service, ner_service, info_extraction_service
    ocr_service = ocr_svc_instance
    classifier_service = classifier_svc_instance
    ner_service = ner_svc_instance
    info_extraction_service = info_ext_svc_instance


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


@information_bp.route('extract-information', methods=['POST'])
def extract_information_endpoint():
    """
    Endpoint untuk mengunggah file, melakukan OCR, lalu mengekstrak entitas dari teksnya.
    """
    if ocr_service is None or classifier_service is None or ner_service is None:
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

        text_for_classification = ocr_result.get("text_for_classification")
        text_for_ner = ocr_result.get("text_for_ner")

        logger.info("Memulai klasifikasi pada teks hasil OCR...")
        classification_result = classifier_service.classify_text(text_for_classification)

        logger.info("Memulai ekstraksi entitas pada teks hasil OCR...")
        entities = ner_service.predict_entities_text(text_for_ner)

        sanitized_entities = sanitize_for_json(entities)

        logger.info("Memulai ekstraksi informasi...")
        structure_data = info_extraction_service.process_extraction(
            classification=classification_result[0].get('label'),
            text_for_ner=text_for_ner,
            entities=sanitized_entities,
            filename=ocr_result.get('file_name')
        )

        # Format respons JSON
        return jsonify({
            'data': structure_data
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
