import os
import random
from core.config import settings
import cv2
import numpy as np


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

    print(f"Memulai pra-pemrosesan untuk Halaman {page_number + 1} (ID: {id_numerik})...")
    if image_data is None:
        print("Error: Tidak ada data gambar untuk diproses.")
        return None, None  # Kembalikan juga None untuk gambar grayscale asli

    # Pastikan gambar dalam format 3 channel jika berwarna, atau konversi ke gray
    if len(image_data.shape) == 3 and image_data.shape[2] == 3:
        original_bgr_for_cropping = image_data.copy()
        gray = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
    elif len(image_data.shape) == 2:  # Sudah grayscale
        original_bgr_for_cropping = cv2.cvtColor(image_data, cv2.COLOR_GRAY2BGR)  # Buat versi BGR jika input gray
        gray = image_data.copy()
    else:
        print("Format gambar tidak didukung untuk pra-pemrosesan.")
        return None, None

    cv2.imwrite(os.path.join(folder_target, "debug_0a_original_for_crop.png"), original_bgr_for_cropping)
    cv2.imwrite(os.path.join(folder_target, "debug_0b_grayscale_initial.png"), gray)

    original_width, original_height = gray.shape[:2]
    print(f"Dimensi Halaman {page_number + 1} (T x L): {original_height} x {original_width} piksel.")

    # --- MASKING LOGO KONDISIONAL HANYA UNTUK HALAMAN PERTAMA (indeks 0) ---
    if page_number == 0:
        print(f"--- Menerapkan Masking Logo untuk Halaman {page_number + 1} ---")

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
                print(f"Konten terdeteksi di area logo kiri [{y0_L}:{y1_L}, {x0_L}:{x1_L}] dan di-mask.")

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
                print(f"Konten terdeteksi di area logo kanan [{y0_R}:{y1_R}, {x0_R}:{x1_R}] dan di-mask.")
            else:
                print(f"Tidak ada konten signifikan terdeteksi di area logo kanan.")
        else:
            print(f"Koordinat logo kanan di luar batas gambar.")

        cv2.imwrite(os.path.join(folder_target, "debug_0b_after_logo_masking.png"), gray)
    else:
        print(f"--- Tidak Menerapkan Masking Logo untuk Halaman {page_number + 1} ---")

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
        cv2.imwrite(os.path.join(folder_target, "debug_2_binary_for_ocr.png"), binary_image)
    except Exception as e:
        print(f"Error saat binarisasi: {e}")
        return None, None

    return binary_image, original_bgr_for_cropping
