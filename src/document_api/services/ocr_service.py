import os
import logging
import uuid
from typing import Dict, Any

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

from src.document_api.utils.preprocessing_image import preprocess_image_data
from src.document_api.utils.preprocessing_table_data import extract_table_grid_from_page, page_after_line_removal
from src.document_api.utils.postprocessing_text import intelligent_postprocessing


class OCRError(Exception):
    """Base exception class untuk semua error terkait OCR."""
    pass


class TesseractNotFoundError(OCRError):
    """Dilemparkan ketika Tesseract tidak bisa ditemukan atau dieksekusi."""
    pass


class PDFConversionError(OCRError):
    """Dilemparkan ketika konversi PDF ke gambar gagal."""
    pass


class ImageReadError(OCRError):
    """Dilemparkan ketika file gambar tidak bisa dibaca."""
    pass


logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self, tesseract_cmd: str, poppler_path: str = None):
        """
        Inisialisasi service dengan dependensi yang dibutuhkan (Dependency Injection).

        Args:
            tesseract_cmd: Path absolut ke executable Tesseract.
            poppler_path: Path absolut ke library Poppler (opsional, untuk Windows).
        """
        if not os.path.exists(tesseract_cmd):
            raise TesseractNotFoundError(f"Tesseract executable tidak ditemukan di path: {tesseract_cmd}")

        pytesseract.tesseract_cmd = tesseract_cmd
        self.poppler_path = poppler_path
        logger.info(f"OCRService diinisialisasi dengan Tesseract di: {tesseract_cmd}")

    @staticmethod
    def _ocr_core(image_data: np.ndarray, psm: int = 6) -> str:
        """
        Wrapper privat untuk panggilan Pytesseract. Menggunakan PSM 6 untuk menjaga struktur.
        """
        if image_data is None:
            logger.warning("Mencoba OCR pada data gambar yang None, mengembalikan string kosong.")
            return ""

        try:
            # Konversi BGR (OpenCV) ke RGB (PIL)
            pil_image = Image.fromarray(cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB))
            custom_config = f'--oem 3 --psm {psm}'
            logger.info(f"configurasi pytesseract : {custom_config}")
            text = pytesseract.image_to_string(pil_image, lang='ind', config=custom_config)
            return text
        except pytesseract.TesseractError as e:
            logger.error(f"Pytesseract error: {e}", exc_info=True)
            raise OCRError(f"Terjadi error internal saat Tesseract memproses gambar: {e}")
        except Exception as e:
            logger.error(f"Error tak terduga saat konversi gambar atau OCR: {e}", exc_info=True)
            raise OCRError(f"Error tak terduga di dalam _ocr_core: {e}")

    def _process_single_image(self, image_bgr: np.ndarray, debug_id: str, page_num: int) -> str:
        """
        Helper privat untuk memproses satu gambar (dari PDF atau file gambar).
        Ini adalah inti dari prinsip DRY untuk menghindari duplikasi kode.
        """
        logger.info(f"[Debug ID: {debug_id}] Memulai pra-pemrosesan untuk halaman/gambar ke-{page_num + 1}.")

        binary_image, _ = preprocess_image_data(image_bgr, page_number=page_num, id_numerik=debug_id)
        if binary_image is None:
            logger.warning(
                f"[Debug ID: {debug_id}] Pra-pemrosesan gagal untuk halaman {page_num + 1}, halaman dilewati.")
            return ""

        grid_mask = extract_table_grid_from_page(binary_image, debug_id, page_num)
        final_image = page_after_line_removal(binary_image, grid_mask, debug_id, page_num)

        # Fallback jika penghapusan garis gagal, gunakan gambar biner hasil pra-pemrosesan.
        if final_image is None:
            final_image = binary_image

        logger.info(f"[Debug ID: {debug_id}] Melakukan OCR pada gambar final halaman {page_num + 1}...")
        return self._ocr_core(final_image, psm=6)

    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Metode utama untuk mengekstrak teks dari file (PDF atau Gambar).
        Menjalankan OCR sekali dan mengembalikan format untuk NER dan Klasifikasi.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File input tidak ditemukan di: {file_path}")

        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()
        debug_id = str(uuid.uuid4())
        logger.info(f"--- Memulai Pipeline OCR [Debug ID: {debug_id}] untuk file: {os.path.basename(file_path)} ---")

        all_pages_raw_text = []
        page_count = 0

        if file_extension == ".pdf":
            try:
                page_count = pdfinfo_from_path(file_path, poppler_path=self.poppler_path)['Pages']
                images_from_pdf = convert_from_path(file_path, dpi=300, poppler_path=self.poppler_path)
            except Exception as e:
                logger.error(f"Gagal mengonversi PDF: {e}", exc_info=True)
                raise PDFConversionError(f"Gagal memproses file PDF: {e}. Pastikan Poppler terinstal.")

            for i, pil_image in enumerate(images_from_pdf):
                opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                page_raw_text = self._process_single_image(opencv_image, debug_id, i)
                all_pages_raw_text.append(page_raw_text)

        elif file_extension in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
            page_count = 1
            opencv_image = cv2.imread(file_path)
            if opencv_image is None:
                raise ImageReadError(f"Gagal membaca file gambar menggunakan OpenCV: {file_path}")

            page_raw_text = self._process_single_image(opencv_image, debug_id, 0)
            all_pages_raw_text.append(page_raw_text)
        else:
            raise OCRError(f"Format file tidak didukung: {file_extension}")

        full_raw_text = "\n".join(all_pages_raw_text)
        processed_texts = intelligent_postprocessing(full_raw_text)
        logger.info(f"--- Pipeline OCR [Debug ID: {debug_id}] Selesai ---")

        return {
            "text_for_ner": processed_texts["text_for_ner"],
            "text_for_classification": processed_texts["text_for_classification"],
            "page_count": page_count,
            "file_name": os.path.basename(file_path)
        }
