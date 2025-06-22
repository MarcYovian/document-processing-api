import logging
import os
import random
from core.config import settings
import cv2
import numpy as np


def remove_elements_by_contour(binary_image, gray_image_to_clean, id_numerik=None, page_number=0):
    """
    [DIPERBAIKI] Menghapus elemen besar dengan filter LUAS dan RASIO ASPEK.
    """
    logging.info("--- Memulai penghapusan elemen berdasarkan analisis kontur ---")

    cleaned_image = gray_image_to_clean.copy()
    folder_target = None
    if id_numerik:
        folder_target = os.path.join(settings.DEBUG_FILE, str(id_numerik), f"page_{page_number + 1}")

    inverted_binary = cv2.bitwise_not(binary_image)
    if folder_target:
        cv2.imwrite(os.path.join(folder_target, "debug_3a_inverted_binary.png"), inverted_binary)

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 6))

    # Terapkan erosi.
    eroded_image = cv2.erode(inverted_binary, vertical_kernel, iterations=1)
    logging.info("Menerapkan erosi morfologis untuk memisahkan baris teks.")
    if folder_target:
        cv2.imwrite(os.path.join(folder_target, "debug_3b_eroded_image.png"), eroded_image)
    # =================================================================================

    # 2. Cari kontur pada gambar yang SUDAH DIEROSI
    # Ini adalah perubahan kunci. Kita tidak lagi mencari pada inverted_binary asli.
    contours, _ = cv2.findContours(eroded_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    logging.info(f"Total kontur terdeteksi setelah erosi: {len(contours)}")

    # 3. Tentukan nilai ambang (threshold)
    MIN_CONTOUR_AREA = 1500
    MAX_ASPECT_RATIO = 5.0

    removed_count = 0
    for contour in contours:
        area = cv2.contourArea(contour)

        if area > MIN_CONTOUR_AREA:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0

            if aspect_ratio < MAX_ASPECT_RATIO:
                removed_count += 1
                # Timpa kontur pada gambar grayscale dengan warna putih (255)
                # PENTING: Kita tetap menggambar kontur asli, bukan kontur yang sudah terkikis.
                cv2.drawContours(cleaned_image, [contour], -1, (255), thickness=cv2.FILLED)

    logging.info(f"Total kontur dihapus (dianggap ttd/stempel): {removed_count}")
    if folder_target:
        cv2.imwrite(os.path.join(folder_target, "debug_4b_cleaned_grayscale.png"), cleaned_image)

    return cleaned_image


def likely_contains_content(image_region, std_dev_threshold=10.0):
    """
    Placeholder: Fungsi untuk mengecek apakah sebuah region gambar kemungkinan berisi konten.
    Implementasi sederhana berdasarkan standar deviasi.
    """
    if image_region is None or image_region.size == 0:
        return False
    # Jika gambar berwarna, konversi ke gray dulu jika perlu
    if len(image_region.shape) == 3 and image_region.shape[2] == 3:
        image_region_gray = cv2.cvtColor(image_region, cv2.COLOR_BGR2GRAY)
    elif len(image_region.shape) == 2:
        image_region_gray = image_region
    else:
        return False  # Format tidak dikenal

    std_dev = np.std(image_region_gray)
    # print(f"DEBUG likely_contains_content: std_dev = {std_dev}")
    return std_dev > std_dev_threshold


def preprocess_image_data(image_data, page_number=0, std_dev_threshold_logo=15.0, id_numerik=None):
    """
    Melakukan pra-pemrosesan pada data gambar (numpy array) untuk meningkatkan kualitas OCR.
    """

    if id_numerik is None:
        id_numerik = random.randint(100000, 999999)

    folder_target = os.path.join(settings.DEBUG_FILE, str(id_numerik), f"page_{page_number + 1}")
    if not os.path.exists(folder_target):
        os.makedirs(folder_target)

    logging.info(f"Memulai pra-pemrosesan untuk Halaman {page_number + 1} (ID: {id_numerik})...")
    if image_data is None:
        logging.error("Error: Tidak ada data gambar untuk diproses.")
        return None, None  # Kembalikan juga None untuk gambar grayscale asli

    # Pastikan gambar dalam format 3 channel jika berwarna, atau konversi ke gray
    if len(image_data.shape) == 2:  # Jika input sudah grayscale, konversi ke BGR
        image_data = cv2.cvtColor(image_data, cv2.COLOR_GRAY2BGR)
    elif image_data.shape[2] == 4:  # Jika ada alpha channel, buang
        image_data = cv2.cvtColor(image_data, cv2.COLOR_BGRA2BGR)

    original_bgr_for_cropping = image_data.copy()
    cv2.imwrite(os.path.join(folder_target, "debug_0a_original_for_crop.png"), original_bgr_for_cropping)

    original_height, original_width = image_data.shape[:2]
    logging.info(f"Dimensi Halaman {page_number + 1} (T x L): {original_height} x {original_width} piksel.")

    logging.info(f"--- Menerapkan Penghapusan Tanda Tangan Berwarna untuk Halaman {page_number + 1} ---")

    gray = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(os.path.join(folder_target, "debug_0b_grayscale_initial.png"), gray)

    # --- MASKING LOGO KONDISIONAL HANYA UNTUK HALAMAN PERTAMA (indeks 0) ---
    if page_number == 0:
        # Pastikan koordinat logo sesuai dengan dimensi gambar
        # Kita akan bekerja pada gambar 'gray' sebelum diubah ukurannya atau di-deskew secara signifikan
        # Jika Anda melakukan scaling di awal, sesuaikan koordinat logo ini atau lakukan scaling koordinat.
        logging.info(f"--- Menerapkan Masking Logo untuk Halaman {page_number + 1} ---")

        # Cek dan Mask Logo Kiri
        y0_L, y1_L, x0_L, x1_L = settings.LEFT_LOGO_BOX
        y1_L = min(y1_L, original_height);
        x1_L = min(x1_L, original_width)
        if 0 <= y0_L < y1_L and 0 <= x0_L < x1_L:
            left_logo_region = gray[y0_L:y1_L, x0_L:x1_L]
            if likely_contains_content(left_logo_region, std_dev_threshold=std_dev_threshold_logo):
                gray[y0_L:y1_L, x0_L:x1_L] = 255  # Jadikan putih (latar belakang)

        # Cek dan Mask Logo Kanan
        y0_R, y1_R, x0_R, x1_R = settings.RIGHT_LOGO_BOX
        y1_R = min(y1_R, original_height);
        x1_R = min(x1_R, original_width)
        if 0 <= y0_R < y1_R and 0 <= x0_R < x1_R:
            right_logo_region = gray[y0_R:y1_R, x0_R:x1_R]
            if likely_contains_content(right_logo_region, std_dev_threshold=std_dev_threshold_logo):
                gray[y0_R:y1_R, x0_R:x1_R] = 255  # Jadikan putih (latar belakang)
                logging.info(f"Konten terdeteksi di area logo kanan [{y0_R}:{y1_R}, {x0_R}:{x1_R}] dan di-mask.")
            else:
                logging.info(f"Tidak ada konten signifikan terdeteksi di area logo kanan.")
        else:
            logging.info(f"Koordinat logo kanan di luar batas gambar.")

        # (Opsional) Simpan gambar setelah masking logo untuk debugging
        cv2.imwrite(os.path.join(folder_target, "debug_0b_after_logo_masking.png"), gray)
    else:
        logging.info(f"--- Tidak Menerapkan Masking Logo untuk Halaman {page_number + 1} ---")

    # Deskew (meluruskan kemiringan)
    deskewed_gray = gray.copy()
    # try:
    #     edges = cv2.Canny(deskewed_gray, 50, 150, apertureSize=3)
    #     lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=min(original_width, original_height)//10, maxLineGap=20)
    #     if lines is not None:
    #         angles = []
    #         for line_segment in lines:
    #             for x1, y1, x2, y2 in line_segment:
    #                 angle = np.arctan2(y2 - y1, x2 - x1) * 180. / np.pi
    #                 if -10 < angle < 10 and abs(angle) > 0.1: # Filter sudut yang relevan
    #                     angles.append(angle)
    #         if angles:
    #             median_angle = np.median(angles)
    #             (h, w) = deskewed_gray.shape[:2]
    #             center = (w // 2, h // 2)
    #             M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    #             deskewed_gray = cv2.warpAffine(deskewed_gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    #             print(f"Gambar Halaman {page_number+1} diluruskan (deskewed) sebesar {median_angle:.2f} derajat.")
    #             cv2.imwrite(os.path.join(folder_target, "debug_1_deskewed.png"), deskewed_gray)
    # except Exception as e:
    #     print(f"Error saat deskewing Halaman {page_number + 1}: {e}")

    # Binarisasi menggunakan Otsu's Thresholding
    gray_to_binarize = deskewed_gray

    try:
        _, initial_binary_image = cv2.threshold(gray_to_binarize, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite(os.path.join(folder_target, "debug_2a_binary_initial.png"), initial_binary_image)
    except Exception as e:
        logging.error(f"Error saat binarisasi awal: {e}")
        return None, None

    cleaned_gray = remove_elements_by_contour(initial_binary_image, gray, id_numerik=id_numerik,
                                              page_number=page_number)

    try:
        _, binary_image = cv2.threshold(cleaned_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite(os.path.join(folder_target, "debug_2_binary_for_ocr.png"), binary_image)
    except Exception as e:
        logging.error(f"Error saat binarisasi: {e}")
        return None, None

    return binary_image, original_bgr_for_cropping
