import logging
import os
import shutil

from flask import Flask

from .api.classifier import init_classifier_services, classifier_bp
from .api.information_extraction import init_information_services, information_bp
from .api.ner import init_ner_services, ner_bp
from .api.ocr import ocr_bp, init_ocr_service
from .core.config import settings
from .services.classifier_service import TextClassifierService
from .services.information_extraction_service import InformationExtractionService
from .services.ner_service import NERService
from .services.ocr_service import OCRService


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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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

    # Daftarkan blueprint ke aplikasi
    app.register_blueprint(ocr_bp, url_prefix='/documents')
    app.register_blueprint(classifier_bp, url_prefix='/documents')
    app.register_blueprint(ner_bp, url_prefix='/documents')
    app.register_blueprint(information_bp, url_prefix='/documents')

    @app.route('/health')
    def health_check():
        return "OK", 200

    return app
