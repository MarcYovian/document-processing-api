import logging
import sys

# Konfigurasi logging dasar untuk mencetak ke konsol (terminal)
# Ini akan memaksa log untuk muncul saat kita tes manual
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # Arahkan log ke output standar
)

try:
    # Ganti dengan path impor yang benar jika perlu
    from app.services.ocr_service import OCRService

    logging.info("Mencoba membuat instance dari OCRService...")
    # Saat baris ini dijalankan, __init__ dan _find_tesseract_path akan tereksekusi
    service = OCRService()
    logging.info(">>> SUKSES: Instance OCRService berhasil dibuat! Tesseract ditemukan. <<<")

except Exception as e:
    # Jika ada error saat inisialisasi (termasuk FileNotFoundError), akan tertangkap di sini
    logging.error(">>> GAGAL: Terjadi error saat inisialisasi OCRService. <<<", exc_info=True)
