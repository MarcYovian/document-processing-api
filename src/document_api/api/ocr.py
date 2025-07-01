import logging
import os

from flask import Blueprint, request, jsonify
from ..services.ocr_service import OCRService, TesseractNotFoundError, OCRError
from ..utils.file_handler import save_uploaded_file

logger = logging.getLogger(__name__)
ocr_bp = Blueprint('ocr_bp', __name__)

ocr_service: OCRService = None


def init_ocr_service(ocr_svc_instance: ocr_service):
    """Fungsi helper untuk menginisialisasi service saat aplikasi dimulai."""
    global ocr_service
    ocr_service = ocr_svc_instance


@ocr_bp.route('/extract-text', methods=['POST'])
def extract_text_endpoint():
    """
    Endpoint untuk mengunggah file (PDF/Gambar) dan mengekstrak teksnya
    menggunakan OCRService.
    """
    if ocr_service is None:
        logger.error("OCRService belum diinisialisasi.")
        return jsonify({"error": "Layanan OCR tidak tersedia."}), 503 # Service Unavailable

    if 'file' not in request.files:
        return jsonify({"error": "Request harus menyertakan bagian 'file'."}), 400

    file = request.files['file']
    file_path, error = save_uploaded_file(file)
    if error:
        return jsonify({"error": error}), 500

    try:
        # Panggil service untuk melakukan pekerjaan berat
        result = ocr_service.extract_text_from_file(file_path)
        return jsonify({
            'data': {
                "file_name": result.get("file_name"),
                'text': result.get('text_for_ner')
            }
        }), 200

    except FileNotFoundError as e:
        logger.warning(f"File tidak ditemukan selama proses: {e}")
        return jsonify({"error": "File tidak dapat ditemukan di server setelah diunggah."}), 404
    except OCRError as e:
        # Menangkap semua error spesifik dari service OCR
        logger.error(f"Terjadi error OCR yang terkendali: {e}", exc_info=True)
        return jsonify({"error": "terjadi error"}), 500
    except Exception as e:
        # Menangkap semua error tak terduga lainnya
        logger.critical(f"Terjadi error internal server yang tidak terduga: {e}", exc_info=True)
        return jsonify({"error": "Terjadi kesalahan internal pada server."}), 500
    finally:
        # Bagian ini sangat penting: selalu hapus file sementara setelah selesai
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"File sementara berhasil dihapus: {file_path}")
            except OSError as e:
                logger.error(f"Gagal menghapus file sementara: {file_path}. Error: {e}")