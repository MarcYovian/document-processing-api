import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone

from flask import Flask, jsonify

from .api.classifier import init_classifier_services, classifier_bp
from .api.information_extraction import init_information_services, information_bp
from .api.ner import init_ner_services, ner_bp
from .api.ocr import ocr_bp, init_ocr_service
from .api.scanner import init_scanner_api, scanner_bp
from .core.config import settings
from .services.classifier_service import TextClassifierService
from .services.information_extraction_service import InformationExtractionService
from .services.ner_service import NERService
from .services.ocr_service import OCRService
from .services.scan_service import ScanService

logger = logging.getLogger(__name__)


def find_tesseract_path() -> str | None:
    """Fungsi helper untuk menemukan Tesseract di sistem."""
    found_path = shutil.which("tesseract")
    if found_path: return found_path
    default_path = "/usr/bin/tesseract" if os.name != "nt" else r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    return default_path if os.path.exists(default_path) else None


def create_app():
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(settings)
    app.config['UPLOAD_FOLDER'] = settings.UPLOAD_FOLDER

    # Konfigurasi logging bisa dipindahkan ke sini untuk sentralisasi
    if settings.APP_ENV == 'local':
        log_level = logging.DEBUG
        logger.info("Aplikasi berjalan di lingkungan LOKAL, logging diatur ke DEBUG.")
    else:
        log_level = logging.INFO
        logger.info(f"Aplikasi berjalan di lingkungan PRODUKSI ({settings.APP_ENV}), logging diatur ke INFO.")

    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)-8s - %(name)-25s - %(message)s')

    with app.app_context():
        # 1. Buat instance OCRService
        tesseract_path = find_tesseract_path()
        ocr_service_instance = OCRService(
            tesseract_cmd=tesseract_path,
            poppler_path=settings.POPPLER_PATH
        )

        classifier_service_instance = TextClassifierService(
            model_name_or_path=settings.CLASSIFY_MODEL
        )

        ner_service_instance = NERService(
            model_name_or_path=settings.NER_MODEL
        )

        info_ext_svc_instance = InformationExtractionService()

        scan_service_instance = ScanService(
            api_url=settings.ROBOFLOW_API_URL,
            api_key=settings.ROBOFLOW_API_KEY,
            model_id=settings.ROBOFLOW_PROJECT_ID
        )

        init_ocr_service(ocr_service_instance)
        init_classifier_services(
            ocr_svc_instance=ocr_service_instance,
            classifier_svc_instance=classifier_service_instance
        )
        init_ner_services(
            ocr_svc_instance=ocr_service_instance,
            ner_svc_instance=ner_service_instance
        )
        init_information_services(
            ocr_svc_instance=ocr_service_instance,
            classifier_svc_instance=classifier_service_instance,
            ner_svc_instance=ner_service_instance,
            info_ext_svc_instance=info_ext_svc_instance
        )
        init_scanner_api(
            service_instance=scan_service_instance
        )

    # Daftarkan blueprint ke aplikasi
    app.register_blueprint(ocr_bp, url_prefix='/documents')
    app.register_blueprint(classifier_bp, url_prefix='/documents')
    app.register_blueprint(ner_bp, url_prefix='/documents')
    app.register_blueprint(information_bp, url_prefix='/documents')
    app.register_blueprint(scanner_bp, url_prefix='/documents')

    @app.route('/health', methods=['GET'])
    def health_check():
        """
        Melakukan pengecekan kesehatan terperinci pada aplikasi dan dependensinya.
        """
        is_healthy = True
        dependencies_status = {}

        # 1. Cek Tesseract
        try:
            # Cara cepat memeriksa Tesseract adalah dengan menjalankan perintah version
            subprocess.run([tesseract_path, "--version"], check=True, capture_output=True, text=True)
            dependencies_status["ocr_tesseract"] = {"status": "OK"}
        except Exception as e:
            is_healthy = False
            logger.error(f"Health Check Gagal: Tesseract tidak bisa dieksekusi. Error: {e}")
            dependencies_status["ocr_tesseract"] = {"status": "UNHEALTHY", "error": str(e)}

        # 2. Cek Model Klasifikasi
        if classifier_service_instance and classifier_service_instance.classifier:
            dependencies_status["classifier_model"] = {"status": "OK", "model": classifier_service_instance.model_name}
        else:
            is_healthy = False
            logger.error("Health Check Gagal: Model klasifikasi tidak dimuat.")
            dependencies_status["classifier_model"] = {"status": "UNHEALTHY", "model": settings.CLASSIFY_MODEL}

        # 3. Cek Model NER
        if ner_service_instance and ner_service_instance.ner_pipeline:
            dependencies_status["ner_model"] = {"status": "OK", "model": ner_service_instance.model_name}
        else:
            is_healthy = False
            logger.error("Health Check Gagal: Model NER tidak dimuat.")
            dependencies_status["ner_model"] = {"status": "UNHEALTHY", "model": settings.NER_MODEL}

        try:
            is_ok, message = scan_service_instance.check_api_health()
            if is_ok:
                dependencies_status["scan_service_roboflow"] = {"status": "OK"}
            else:
                is_healthy = False
                logger.error(f"Health Check Gagal: Roboflow API. Error: {message}")
                dependencies_status["scan_service_roboflow"] = {"status": "UNHEALTHY", "error": message}
        except Exception as e:
            is_healthy = False
            logger.error(f"Health Check Gagal: Exception saat memeriksa Roboflow API. Error: {e}")
            dependencies_status["scan_service_roboflow"] = {"status": "UNHEALTHY", "error": str(e)}

        # Susun respons JSON
        response_data = {
            "status": "OK" if is_healthy else "UNHEALTHY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dependencies": dependencies_status
        }

        # Tentukan status code HTTP
        status_code = 200 if is_healthy else 503  # 503 Service Unavailable

        return jsonify(response_data), status_code
    return app
