import os
from dotenv import load_dotenv
from typing import Tuple

load_dotenv()


class Settings:
    APP_ENV: str = os.getenv('APP_ENV', 'local')
    APP_DEBUG: bool = os.getenv('APP_DEBUG', 'true').lower() == 'true'
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Tentukan folder debug relatif terhadap root proyek
    DEBUG_FILE: str = os.path.join(BASE_DIR, os.getenv("DEBUG_FILE", "debug"))
    LEFT_LOGO_BOX_RELATIVE: Tuple[int, int, int, int] = (0.0313, 0.1667, 0.0369, 0.1363)  # (80, 425, 122, 450)
    RIGHT_LOGO_BOX_RELATIVE: Tuple[int, int, int, int] = (0.0313, 0.1667, 0.6439, 0.7293)  # (80, 425, 2125, 2407)
    TESSERACT_PATH = os.getenv("TESSERACT_PATH")
    POPPLER_PATH = os.getenv("POPPLER_PATH")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads_for_ocr/")
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff'}
    CLASSIFY_MODEL = os.getenv("CLASSIFY_MODEL", "marcyovian/indobert-church-document-classification")
    NER_MODEL = os.getenv("NER_MODEL", "marcyovian/indobert-church-extraction-document")
    ROBOFLOW_API_URL = os.getenv('ROBOFLOW_API_URL')
    ROBOFLOW_API_KEY = os.getenv('ROBOFLOW_API_KEY')
    ROBOFLOW_PROJECT_ID = os.getenv('ROBOFLOW_PROJECT_ID')


settings = Settings()