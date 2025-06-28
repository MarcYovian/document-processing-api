import logging
import os
import sys

# 1. Tambahkan print statement di baris paling awal untuk memastikan file ini dieksekusi.
print(">>> Skrip run.py mulai dieksekusi.")
base_dir = os.path.dirname(os.path.abspath(__file__))

print(base_dir)
logs_dir = os.path.join(base_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)
log_file_path = os.path.join(logs_dir, 'app.log')

print(f">>> File log akan disimpan di: {log_file_path}")

logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

logger = logging.getLogger(__name__)
logger.info("Konfigurasi logging berhasil. Aplikasi dimulai.")\

try:
    # 4. Lakukan impor di dalam blok try-except untuk menangkap error
    print(">>> Mencoba mengimpor 'app' dan 'settings'...")
    from app.main import app
    from core.config import settings

    print(">>> Impor 'app' dan 'settings' berhasil.")
except ImportError as e:
    logger.error(f"FATAL ERROR: Gagal melakukan impor. Error: {e}")
    # Keluar jika impor gagal, karena tidak ada yang bisa dijalankan
    sys.exit(1)

if __name__ == '__main__':
    logger.info("Server akan dimulai dari dalam blok __main__.")
    logger.info(f"Folder upload sementara: {os.path.abspath(settings.UPLOAD_FOLDER)}")
    if settings.DEBUG_FILE:
        logger.info(f"Folder debug OCRService: {os.path.abspath(settings.DEBUG_FILE)}")

    app.run(host='0.0.0.0', port=5000, debug=False)

else:
    logger.warning("File ini diimpor oleh modul lain, bukan dijalankan langsung.")