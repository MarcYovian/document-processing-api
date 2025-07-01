import logging
import os
import random
from src.document_api.core.config import settings
import cv2
import numpy as np


logger = logging.getLogger(__name__)


def remove_stamp_and_signature(image_bgr: np.ndarray, page_number: int = 0, id_numerik=None) -> np.ndarray:
    """
    Mencoba menghapus stempel dan tanda tangan berwarna dari gambar BGR.
    Khusus untuk halaman pertama (page_number == 0), fungsi ini akan melindungi
    area header agar warna logo tidak ikut terhapus.

    Args:
        image_bgr: Gambar input dalam format BGR.
        page_number: Nomor halaman saat ini (dimulai dari 0).

    Returns:
        Gambar BGR di mana area stempel/tanda tangan telah diubah menjadi putih.
    """
    if settings.APP_DEBUG:
        if id_numerik is None:
            id_numerik = random.randint(100000, 999999)

        folder_target = os.path.join(settings.DEBUG_FILE, str(id_numerik), f"page_{page_number + 1}")
        if not os.path.exists(folder_target):
            os.makedirs(folder_target)

        debug_folder = os.path.join(folder_target, f"page_{page_number + 1}_debug_stamp_removal")
        if not os.path.exists(debug_folder):
            os.makedirs(debug_folder)

        cv2.imwrite(os.path.join(debug_folder, "0_original.png"), image_bgr)

    logger.info(f"Mencoba menghapus stempel/tanda tangan untuk Halaman {page_number + 1}.")

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(debug_folder, "1_hsv_representation.png"), hsv)

    # Definisi rentang warna (tetap sama)
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    lower_purple = np.array([130, 40, 40])
    upper_purple = np.array([170, 255, 255])
    lower_cyan = np.array([80, 50, 50])
    upper_cyan = np.array([100, 255, 255])
    lower_greenish = np.array([40, 40, 40])
    upper_greenish = np.array([85, 255, 255])
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([30, 255, 255])
    lower_muted_brown_green = np.array([15, 25, 25])
    upper_muted_brown_green = np.array([45, 100, 120])
    lower_purple_gray = np.array([120, 20, 20])
    upper_purple_gray = np.array([160, 150, 150])

    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    mask_purple = cv2.inRange(hsv, lower_purple, upper_purple)
    mask_cyan = cv2.inRange(hsv, lower_cyan, upper_cyan)
    mask_greenish = cv2.inRange(hsv, lower_greenish, upper_greenish)
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_muted_brown_green = cv2.inRange(hsv, lower_muted_brown_green, upper_muted_brown_green)
    mask_purple_gray = cv2.inRange(hsv, lower_purple_gray, upper_purple_gray)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(debug_folder, "2a_mask_blue.png"), mask_blue)
        cv2.imwrite(os.path.join(debug_folder, "2b_mask_purple.png"), mask_purple)
        cv2.imwrite(os.path.join(debug_folder, "2c_mask_cyan.png"), mask_cyan)
        cv2.imwrite(os.path.join(debug_folder, "2d_mask_greenish.png"), mask_greenish)
        cv2.imwrite(os.path.join(debug_folder, "2e_mask_yellow.png"), mask_yellow)
        cv2.imwrite(os.path.join(debug_folder, "2f_mask_muted_brown_green.png"), mask_muted_brown_green)
        cv2.imwrite(os.path.join(debug_folder, "2g_mask_purple_gray.png"), mask_purple_gray)

    combined_mask_1 = cv2.bitwise_or(mask_blue, mask_purple)
    combined_mask_2 = cv2.bitwise_or(combined_mask_1, mask_cyan)
    combined_mask_3 = cv2.bitwise_or(combined_mask_2, mask_greenish)
    combined_mask_4 = cv2.bitwise_or(combined_mask_3, mask_yellow)
    combined_mask_5 = cv2.bitwise_or(combined_mask_4, mask_muted_brown_green)
    combined_mask = cv2.bitwise_or(combined_mask_5, mask_purple_gray)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(debug_folder, "3_mask_combined.png"), combined_mask)

    # --- PERUBAHAN: Logika untuk melindungi header di halaman pertama ---
    if page_number == 0:
        logger.info("Halaman pertama terdeteksi, menerapkan masker pelindung untuk header.")
        # Definisikan area header. Di sini, kita asumsikan header adalah 15% bagian atas dari gambar.
        # Anda bisa menyesuaikan nilai 0.15 ini sesuai kebutuhan.
        h, w, _ = image_bgr.shape
        header_height = int(h * 0.15)

        # Buat masker pelindung: putih di semua tempat, KECUALI hitam di area header.
        # Masker ini akan membatalkan deteksi warna di dalam area header.
        protection_mask = np.full((h, w), 255, dtype=np.uint8)
        cv2.rectangle(protection_mask, (0, 0), (w, header_height), (0, 0, 0), -1)

        # Terapkan masker pelindung ke masker warna gabungan.
        # Ini akan memastikan area header di 'combined_mask' menjadi hitam (tidak terdeteksi).
        combined_mask = cv2.bitwise_and(combined_mask, protection_mask)
        if settings.APP_DEBUG:
            cv2.imwrite(os.path.join(debug_folder, "4_mask_after_header_protection.png"), combined_mask)

    # Lanjutkan proses pembersihan seperti biasa dengan masker yang sudah dimodifikasi
    # kernel_opening = np.ones((2, 2), np.uint8)
    # mask_no_noise = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_opening, iterations=1)
    # # DEBUG: Simpan peta noda setelah bintik-bintik kecil dihilangkan.
    # cv2.imwrite(os.path.join(debug_folder, "5a_mask_after_noise_removal.png"), mask_no_noise)

    # 5b. Tebalkan dan sambungkan goresan yang terputus
    kernel_dilation = np.ones((3, 3), np.uint8)
    dilated_mask = cv2.dilate(combined_mask, kernel_dilation, iterations=1)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(debug_folder, "5b_mask_final_dilated.png"), dilated_mask)

    white_background = np.full(image_bgr.shape, 255, dtype=np.uint8)
    image_no_stamp_signature = cv2.bitwise_and(image_bgr, image_bgr, mask=cv2.bitwise_not(dilated_mask))
    white_overlay = cv2.bitwise_and(white_background, white_background, mask=dilated_mask)
    cleaned_image_bgr = cv2.add(image_no_stamp_signature, white_overlay)
    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(debug_folder, "6_final_cleaned_image.png"), cleaned_image_bgr)

    logger.info("Proses penghapusan stempel dan tanda tangan selesai.")
    return cleaned_image_bgr


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
    if settings.APP_DEBUG:
        if id_numerik is None:
            id_numerik = random.randint(100000, 999999)

        folder_target = os.path.join(settings.DEBUG_FILE, str(id_numerik), f"page_{page_number + 1}")
        if not os.path.exists(folder_target):
            os.makedirs(folder_target)

    logger.info(f"Memulai pra-pemrosesan untuk Halaman {page_number + 1} (ID: {id_numerik})...")
    if image_data is None:
        logger.error("Error: Tidak ada data gambar untuk diproses.")
        return None, None  # Kembalikan juga None untuk gambar grayscale asli

    if len(image_data.shape) == 3 and image_data.shape[2] == 3:
        logger.info("Gambar berwarna terdeteksi, menjalankan penghapusan stempel/tanda tangan.")
        image_cleaned_bgr = remove_stamp_and_signature(image_data, page_number=page_number, id_numerik=id_numerik)
        # Simpan untuk debug jika perlu
        if settings.APP_DEBUG:
            cv2.imwrite(os.path.join(folder_target, "debug_0_after_stamp_removal.png"), image_cleaned_bgr)
    else:
        logger.warning("Gambar input bukan berwarna (BGR), melewati langkah penghapusan stempel.")
        image_cleaned_bgr = image_data

    # Pastikan gambar dalam format 3 channel jika berwarna, atau konversi ke gray
    if len(image_cleaned_bgr.shape) == 3 and image_cleaned_bgr.shape[2] == 3:
        original_bgr_for_cropping = image_cleaned_bgr.copy()
        gray = cv2.cvtColor(image_cleaned_bgr, cv2.COLOR_BGR2GRAY)
    elif len(image_cleaned_bgr.shape) == 2:  # Sudah grayscale
        original_bgr_for_cropping = cv2.cvtColor(image_cleaned_bgr, cv2.COLOR_GRAY2BGR)
        gray = image_cleaned_bgr.copy()
    else:
        logger.error("Format gambar tidak didukung untuk pra-pemrosesan.")
        return None, None

    if settings.APP_DEBUG:
        cv2.imwrite(os.path.join(folder_target, "debug_0a_original_for_crop.png"), original_bgr_for_cropping)
        cv2.imwrite(os.path.join(folder_target, "debug_0b_grayscale_initial.png"), gray)

    original_width, original_height = gray.shape[:2]
    logger.info(f"Dimensi Halaman {page_number + 1} (T x L): {original_height} x {original_width} piksel.")

    # --- MASKING LOGO KONDISIONAL HANYA UNTUK HALAMAN PERTAMA (indeks 0) ---
    if page_number == 0:
        logger.info(f"--- Menerapkan Masking Logo untuk Halaman {page_number + 1} ---")

        # --- Cek dan Mask Logo Kiri (Menggunakan Koordinat Relatif) ---
        # Ambil koordinat relatif dari settings
        y0_rel_L, y1_rel_L, x0_rel_L, x1_rel_L = settings.LEFT_LOGO_BOX_RELATIVE
        # Hitung koordinat absolut berdasarkan dimensi gambar saat ini
        y0_L = int(y0_rel_L * original_height)
        y1_L = int(y1_rel_L * original_height)
        x0_L = int(x0_rel_L * original_width)
        x1_L = int(x1_rel_L * original_width)

        if 0 <= y0_L < y1_L and 0 <= x0_L < x1_L:
            left_logo_region = gray[y0_L:y1_L, x0_L:x1_L]
            if likely_contains_content(left_logo_region, std_dev_threshold=std_dev_threshold_logo):
                gray[y0_L:y1_L, x0_L:x1_L] = 255  # Jadikan putih (latar belakang)
                logger.info(f"Konten terdeteksi di area logo kiri [{y0_L}:{y1_L}, {x0_L}:{x1_L}] dan di-mask.")

        # --- Cek dan Mask Logo Kanan (Menggunakan Koordinat Relatif) ---
        # Ambil koordinat relatif dari settings
        y0_rel_R, y1_rel_R, x0_rel_R, x1_rel_R = settings.RIGHT_LOGO_BOX_RELATIVE
        # Hitung koordinat absolut berdasarkan dimensi gambar saat ini
        y0_R = int(y0_rel_R * original_height)
        y1_R = int(y1_rel_R * original_height)
        x0_R = int(x0_rel_R * original_width)
        x1_R = int(x1_rel_R * original_width)

        if 0 <= y0_R < y1_R and 0 <= x0_R < x1_R:
            right_logo_region = gray[y0_R:y1_R, x0_R:x1_R]
            if likely_contains_content(right_logo_region, std_dev_threshold=std_dev_threshold_logo):
                gray[y0_R:y1_R, x0_R:x1_R] = 255
                logger.info(f"Konten terdeteksi di area logo kanan [{y0_R}:{y1_R}, {x0_R}:{x1_R}] dan di-mask.")
            else:
                logger.info(f"Tidak ada konten signifikan terdeteksi di area logo kanan.")
        else:
            logger.info(f"Koordinat logo kanan di luar batas gambar.")

        if settings.APP_DEBUG:
            cv2.imwrite(os.path.join(folder_target, "debug_0b_after_logo_masking.png"), gray)
    else:
        logger.info(f"--- Tidak Menerapkan Masking Logo untuk Halaman {page_number + 1} ---")

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
        _, binary_image = cv2.threshold(gray_to_binarize, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if settings.APP_DEBUG:
            cv2.imwrite(os.path.join(folder_target, "debug_2_binary_for_ocr.png"), binary_image)
    except Exception as e:
        logger.error(f"Error saat binarisasi: {e}")
        return None, None

    return binary_image, original_bgr_for_cropping
