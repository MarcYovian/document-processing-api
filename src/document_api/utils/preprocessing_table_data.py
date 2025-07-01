import logging

import cv2
import os
import numpy as np

from src.document_api.core.config import settings


def extract_table_grid_from_page(binary_page_for_lines, id_numerik, page_number):
    if settings.APP_DEBUG:
        folder_target_page = os.path.join(settings.DEBUG_FILE, str(id_numerik), f"page_{page_number + 1}")
        if not os.path.exists(folder_target_page):
            os.makedirs(folder_target_page)

    logging.info(f"\n--- Memulai Deteksi Grid Tabel dari Halaman {page_number + 1} ---")
    if binary_page_for_lines is None:
        logging.error(f"Tidak ada gambar biner untuk ekstraksi grid di Halaman {page_number + 1}.")
        return None

    page_height, page_width = binary_page_for_lines.shape[:2]

    # Invert gambar biner agar garis menjadi putih untuk deteksi morfologi
    # (Karena binary_page_for_lines memiliki garis hitam)
    inverted_binary_page = cv2.bitwise_not(binary_page_for_lines)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(folder_target_page, f"debug_3a_inverted_binary_page.png"), inverted_binary_page)

    # 1. Deteksi Garis Horizontal
    horizontal_kernel_length = max(15, page_width // 30)  # Pastikan kernel tidak terlalu kecil
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_kernel_length, 1))
    img_temp_horizontal = cv2.erode(inverted_binary_page, horizontal_kernel, iterations=2)
    horizontal_lines_img = cv2.dilate(img_temp_horizontal, horizontal_kernel, iterations=2)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(folder_target_page, f"debug_3b_horizontal_lines.png"), horizontal_lines_img)

    # 2. Deteksi Garis Vertikal
    vertical_kernel_length = max(15, page_height // 30)  # Pastikan kernel tidak terlalu kecil
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_kernel_length))
    img_temp_vertical = cv2.erode(inverted_binary_page, vertical_kernel, iterations=2)
    vertical_lines_img = cv2.dilate(img_temp_vertical, vertical_kernel, iterations=2)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(folder_target_page, f"debug_3c_vertical_lines.png"), vertical_lines_img)

    # 3. Gabungkan garis untuk mendapatkan grid tabel
    table_grid_mask = cv2.add(horizontal_lines_img, vertical_lines_img)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(folder_target_page, f"debug_3d_table_grid_mask.png"), table_grid_mask)

    # Cek apakah ada sesuatu di table_grid_mask (apakah ada garis yang terdeteksi)
    if np.sum(table_grid_mask) == 0:  # Jika semua piksel hitam (tidak ada garis putih terdeteksi)
        logging.info(f"Tidak ada grid tabel (garis) yang terdeteksi dengan jelas di Halaman {page_number + 1}.")
        return None

    logging.info(f"--- Berhasil Ekstraksi Grid Tabel untuk Halaman {page_number + 1} ---")
    return table_grid_mask


def page_after_line_removal(binary_page_with_lines, table_grid_mask, id_numerik, page_number):
    if settings.APP_DEBUG:
        folder_target = os.path.join(settings.DEBUG_FILE, str(id_numerik), f"page_{page_number + 1}")
        if not os.path.exists(folder_target):
            os.makedirs(folder_target)

    logging.info(f"\n--- Mempersiapkan Halaman {page_number + 1} Setelah Penghapusan Garis ---")

    if binary_page_with_lines is None:
        logging.info(f"Tidak ada gambar biner input untuk Halaman {page_number + 1}.")
        return None
    if table_grid_mask is None:
        logging.info(f"Tidak ada masker grid tabel untuk Halaman {page_number + 1}, menggunakan gambar biner asli.")
        # Simpan gambar biner asli jika tidak ada masker, agar alur debug konsisten
        if settings.APP_DEBUG:
            debug_path_no_removal = os.path.join(folder_target, f"debug_5_no_lines_removed_used_as_is.png")
            cv2.imwrite(debug_path_no_removal, binary_page_with_lines)
        return binary_page_with_lines  # Kembalikan gambar biner asli jika tidak ada masker

    image_lines_removed = binary_page_with_lines.copy()

    # Pastikan table_grid_mask adalah biner (0 dan 255)
    _, table_grid_mask_thresh = cv2.threshold(table_grid_mask, 127, 255, cv2.THRESH_BINARY)

    # Sedikit dilasi pada masker mungkin membantu menutup garis sepenuhnya
    # kernel_dilation_mask = np.ones((2,2), np.uint8)
    # dilated_table_grid_mask = cv2.dilate(table_grid_mask_thresh, kernel_dilation_mask, iterations=1)
    # image_lines_removed[dilated_table_grid_mask == 255] = 255 # Latar adalah putih

    image_lines_removed[table_grid_mask_thresh == 255] = 255  # Latar adalah putih

    if settings.APP_DEBUG:
        debug_path_lines_removed = os.path.join(folder_target, f"debug_5_lines_removed.png")
        cv2.imwrite(debug_path_lines_removed, image_lines_removed)
        logging.info(f"Gambar setelah penghapusan garis disimpan sebagai: {debug_path_lines_removed}")

    return image_lines_removed
