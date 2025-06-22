import os
import random
import logging
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from core.config import settings
from app.utils.preprocessing_image import preprocess_image_data
from app.utils.preprocessing_table_data import extract_table_grid_from_page, page_after_line_removal
from app.utils.postprocessing_text import preprocess_text


class OCRService:
    def __init__(self, tesseract_cmd_path=None):
        if tesseract_cmd_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path

    @staticmethod
    def ocr_core(image_data, lang='ind', psm=4, oem=3, whitelist=''):
        """
        Melakukan OCR pada data gambar yang sudah diproses menggunakan Tesseract.
        """
        if image_data is None:
            return "Error: Tidak ada data gambar untuk di-OCR."
        logging.info("Memulai proses OCR dengan Tesseract...")
        try:
            pil_image = Image.fromarray(image_data)  # Ini bisa jika formatnya tepat

            custom_config = f'--oem {oem} --psm {psm}'
            if whitelist:
                custom_config += f' -c tessedit_char_whitelist="{whitelist}"'

            text = pytesseract.image_to_string(pil_image, lang=lang, config=custom_config)
            logging.info(f"Pytesseract config: {custom_config}")
            logging.info("Proses OCR selesai.")
            return text
        except pytesseract.TesseractNotFoundError:
            logging.error("Error: Tesseract tidak ditemukan. Pastikan sudah terinstal dan ada di PATH.")
            return "[Error OCR: Tesseract tidak ditemukan]"
        except Exception as e:
            return f"[Error OCR: {e}]"

    def extract_text(self, file_path="", std_dev_threshold_logo=15.0):
        logging.info(f"\n--- Memulai Pipeline OCR untuk: {file_path} ---")
        filename, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()

        # Buat id_numerik unik untuk proses ini
        id_numerik = random.randint(100000, 999999)

        if not os.path.exists(settings.DEBUG_FILE):
            os.makedirs(settings.DEBUG_FILE)
        base_folder_for_id = os.path.join(settings.DEBUG_FILE, str(id_numerik))
        if not os.path.exists(base_folder_for_id):
            os.makedirs(base_folder_for_id)
            logging.info(f"Folder debug utama untuk ID {id_numerik} dibuat di: {base_folder_for_id}")

        full_document_text_parts = []

        if file_extension == ".pdf":
            logging.info("File PDF terdeteksi. Mengonversi PDF ke gambar...")
            try:
                images_from_pdf = convert_from_path(
                    file_path,
                    dpi=300,
                    poppler_path=settings.POPPLER_PATH
                )
                if not images_from_pdf:
                    return "Gagal mengonversi PDF (tidak ada halaman)."
            except Exception as e:
                return (f"Gagal mengonversi PDF: {e}. Pastikan Poppler terinstal dan ada di PATH sistem Anda, atau set "
                        f"poppler_path di convert_from_path.")

            for i, pil_image_page in enumerate(images_from_pdf):
                logging.info(f"\nMemproses halaman PDF ke-{i + 1} dari {len(images_from_pdf)}...")
                opencv_image_page_bgr = cv2.cvtColor(np.array(pil_image_page), cv2.COLOR_RGB2BGR)

                binary_page_for_ocr_and_lines, original_bgr_for_cropping = \
                    preprocess_image_data(opencv_image_page_bgr, page_number=i,
                                          std_dev_threshold_logo=std_dev_threshold_logo, id_numerik=id_numerik)

                if binary_page_for_ocr_and_lines is None:
                    page_text_content = f"\n[Gagal pra-pemrosesan halaman]\n"
                    full_document_text_parts.append(page_text_content)
                    continue

                table_grid_mask_hasil = extract_table_grid_from_page(
                    binary_page_for_ocr_and_lines,
                    id_numerik,
                    i
                )

                image_final_ocr_ready = page_after_line_removal(
                    binary_page_for_ocr_and_lines,
                    table_grid_mask_hasil,  # Bisa None jika tidak ada grid
                    id_numerik,
                    i
                )

                if image_final_ocr_ready is None:  # Jika page_after_line_removal gagal
                    image_final_ocr_ready = binary_page_for_ocr_and_lines  # Fallback

                logging.info(f"Melakukan OCR final di Halaman {i + 1}...")
                # PSM 3 (Auto Page Segmentation) atau PSM 4 (Single Column) mungkin cocok di sini
                # atau PSM 11 (Sparse text) jika teksnya sangat tersebar.
                general_text_on_page = self.ocr_core(image_final_ocr_ready, psm=4, lang='ind')  # Coba PSM 3
                cleaned_general_text = preprocess_text(general_text_on_page)

                page_text_content = f"{cleaned_general_text} "
                full_document_text_parts.append(page_text_content)

            final_ocr_text = "".join(full_document_text_parts)

        elif file_extension in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
            opencv_image_bgr = cv2.imread(file_path)
            if opencv_image_bgr is None: return "Gagal membaca file gambar."

            binary_page_for_ocr_and_lines, original_bgr_for_cropping = \
                preprocess_image_data(opencv_image_bgr, page_number=0,
                                      std_dev_threshold_logo=std_dev_threshold_logo, id_numerik=id_numerik)

            if binary_page_for_ocr_and_lines is None:
                return "[Gagal pra-pemrosesan gambar]"

            table_grid_mask_hasil = extract_table_grid_from_page(
                binary_page_for_ocr_and_lines,
                id_numerik,
                0
            )

            image_final_ocr_ready = page_after_line_removal(
                binary_page_for_ocr_and_lines,
                table_grid_mask_hasil,
                id_numerik,
                0
            )

            if image_final_ocr_ready is None:  # Jika page_after_line_removal gagal
                image_final_ocr_ready = binary_page_for_ocr_and_lines  # Fallback

            logging.info(f"Melakukan OCR final pada gambar...")
            general_text_on_page = self.ocr_core(image_final_ocr_ready, psm=4, lang='ind')
            cleaned_general_text = preprocess_text(general_text_on_page)

            final_ocr_text = f"{cleaned_general_text}"
        else:
            return "Format file tidak didukung. Hanya PDF, PNG, JPG, JPEG, BMP, TIFF."

        logging.info(f"--- Pipeline OCR Selesai untuk: {file_path} ---")
        return final_ocr_text.strip()
