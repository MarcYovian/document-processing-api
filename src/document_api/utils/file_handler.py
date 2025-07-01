import logging
import os

from werkzeug.utils import secure_filename

from ..core.config import settings

logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    """
    Memeriksa apakah ekstensi file diizinkan berdasarkan pengaturan.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS


def save_uploaded_file(file) -> tuple[str | None, str | None]:
    """
    Menyimpan file yang diunggah ke folder UPLOAD_FOLDER dengan return yang konsisten.

    Args:
        file: Objek file dari request.files.

    Returns:
        Sebuah tuple (file_path, error_message).
        - Jika sukses: (str, None) -> ('/path/to/file.pdf', None)
        - Jika gagal: (None, str) -> (None, "Pesan error di sini")
    """
    # Validasi 1: Apakah ada file yang benar-benar dikirim?
    if not file or file.filename == '':
        error_msg = "Tidak ada file yang dipilih atau nama file kosong."
        logger.warning(error_msg)
        return None, error_msg

    # Validasi 2: Apakah format file diizinkan?
    if not allowed_file(file.filename):
        allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
        error_msg = f"Format file tidak didukung. Hanya format berikut yang diizinkan: {allowed}"
        logger.warning(error_msg)
        return None, error_msg

    try:
        # Amankan nama file untuk mencegah masalah keamanan
        filename = secure_filename(file.filename)
        file_path = os.path.join(settings.UPLOAD_FOLDER, filename)

        # Simpan file
        file.save(file_path)
        logger.info(f"File berhasil disimpan di: {file_path}")

        # Jika sukses, kembalikan path dan None untuk error
        return file_path, None

    except Exception as e:
        # Jika terjadi error apa pun saat menyimpan, catat dan kembalikan pesan error
        error_msg = f"Gagal menyimpan file di server: {e}"
        logger.error(error_msg, exc_info=True)  # exc_info=True akan mencatat traceback
        return None, "Terjadi kesalahan internal saat menyimpan file."
