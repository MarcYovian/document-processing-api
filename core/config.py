from typing import Tuple


class Settings:
    DEBUG_FILE: str = "debug"
    LEFT_LOGO_BOX: Tuple[int, int, int, int] = (80, 425, 122, 450)
    RIGHT_LOGO_BOX: Tuple[int, int, int, int] = (80, 425, 2125, 2407)
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"
    UPLOAD_FOLDER = 'uploads_for_ocr/'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff'}
    MODEL_PATH = "C:/Users/marce/Documents/Kuliah/Tugas Akhir/document-processing-v2/models_store/"
    CLASSIFY_MODEL = "marcyovian/indobert-church-document-classification"
    NER_MODEL = "marcyovian/indobert-church-extraction-document"


settings = Settings()