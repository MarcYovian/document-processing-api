import os
from dotenv import load_dotenv
from typing import Tuple

load_dotenv()


class Settings:
    DEBUG_FILE: str = os.getenv("DEBUG_FILE", "debug")
    LEFT_LOGO_BOX: Tuple[int, int, int, int] = (80, 425, 122, 450)
    RIGHT_LOGO_BOX: Tuple[int, int, int, int] = (80, 425, 2125, 2407)
    TESSERACT_PATH = os.getenv("TESSERACT_PATH")
    POPPLER_PATH = os.getenv("POPPLER_PATH")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads_for_ocr/")
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff'}
    CLASSIFY_MODEL = os.getenv("CLASSIFY_MODEL", "marcyovian/indobert-church-document-classification")
    NER_MODEL = os.getenv("NER_MODEL", "marcyovian/indobert-church-extraction-document")


settings = Settings()