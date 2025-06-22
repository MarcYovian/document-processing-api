import os
from app.main import app  # Impor objek 'app' dari file app/main.py
from core.config import settings  # Impor settings untuk menampilkan pesan


if __name__ == '__main__':
    # Pindahkan semua logika untuk menjalankan server ke sini
    print("Pastikan Tesseract OCR terinstal dan ada di PATH atau TESSERACT_CMD_PATH sudah benar.")
    print("Untuk PDF, pastikan Poppler terinstal dan ada di PATH.")
    print(f"Folder upload sementara: {os.path.abspath(settings.UPLOAD_FOLDER)}")
    if settings.DEBUG_FILE:
        print(f"Folder debug OCRService: {os.path.abspath(settings.DEBUG_FILE)}")

    # Jalankan server dari objek app yang sudah diimpor
    app.run(host='0.0.0.0', port=5000, debug=True)