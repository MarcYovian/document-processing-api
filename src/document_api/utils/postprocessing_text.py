import re
from unidecode import unidecode
import logging

logger = logging.getLogger(__name__)


def apply_rule_based_corrections(text):
    """
    Fungsi khusus untuk menerapkan koreksi berbasis aturan dari dictionary.
    """
    # Definisikan kamus koreksi Anda di sini
    corrections_dict = {
        # --- KESALAHAN SPESIFIK DARI OCR ---
        r"\bJNAVENTURA\b": "BONAVENTURA",
        r"\bSldoarjo\b": "Sidoarjo",
        r"\bSidoario\b": "Sidoarjo",
        r"\bKaran\s*KARANGPILANG\b": "Karangpilang",
        r"\bKarangpllang\b": "Karangpilang",
        r"\bFebruariari\b": "Februari",
        r"\bFebruan\b": "Februari",
        r"\bSdoarjo\b": "Sidoarjo",
        r"\bKewa\b": "Ketua",
        r"\bWilah\b": "Wilayah",
        r"\bGriva\b": "Griya",
        r"\bAROKI\b": "PAROKI",
        r"\bDIONISITS\b": "DIONISIUS",
        r'\b(No|Hal|Lampiran|Perihal)l-': r'\1: -',
        r'\b(No|Hal|Lampiran|Perihal)\s*l-': r'\1 : -',
        r'\b(No|Hal|Lampiran|Perihal)\s*--\s*:-': r'\1: -',
        r'\b/II1/\b': '/III/',
        r'\b/I1/\b': '/II/',
        r'\b/111/\b': '/III/',
        r'\b/vii\s*1\b': '/VIII',
        r'\b/V1/\b': '/VI/',
        r'\b/V\s*11/\b': '/VI/',
        r'/\s*FEBRUARI\s*1\s*/': '/FEBRUARI/',
        r"\b\s*GPILANG\s*\b": " KARANGPILANG ",
        r"\bREJA\s*\b": " GEREJA ",
        r"\s*SU\s*AYA\s*": " SURABAYA ",
        r"\b\bYth\s*\.\s*\b": "Yth. ",
        r"\bYik\s*\.\s*": "Ytk. ",
        r"\b5\s*\t.\s*": "St. ",
        r"\bYih.\s*": "Ytk. ",
        r"\byih.\s*": "Ytk. ",
        r"\bVYith.\s*": "Ytk. ",
        r"\bYtih\s*\.\s*": "Yth. ",
        r"\bYith\s*\.\s*": "Yth. ",
        r"\bN0\b": "No",
        r'\s*—\s*:': ' :',
        r'\bl\.': '1.',
        r'\bI\b': '',
        r'\bl\b': '',
        r'\b/\s*JUN\s*[1Il]\s*/\b': '/JUNI/',
        r'\b/V\s*1/\b': '/VI/',
        r'\bIRA\b': '',
        r"\bNo\s*\.\s*": "No. ",
        r"(\d{2}\.\d{2})\s*WIB\s*-\s*(\d{2}\.\d{2})\s*WIB": r"\1 - \2 WIB",
        r'(diucapkan terima kasih\.)(?s).*?\b(Ketua Lingkungan,)\b': r'\1\n\n\2',
        r'\b(C\.\s*Heritrianto)(?s).*': r'\1',
    }

    corrected_text = text
    for pattern, replacement in corrections_dict.items():
        try:
            corrected_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
        except re.error as e:
            logger.warning(f"Pola regex tidak valid '{pattern}': {e}")

    return corrected_text


def preprocess_text(text):
    """Lakukan preprocessing pada teks hasil OCR dengan mempertahankan tanda baca penting"""
    try:
        # 1. Normalisasi unicode (handle karakter khusus)
        text = unidecode(text)

        # 2. Ganti newline dengan spasi
        text = text.replace('\n', ' ')
        text = apply_rule_based_corrections(text)

        # 3. Menambahkan spasi antara huruf dan angka
        text = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', text)
        text = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', text)
        text = re.sub(r'(\d{2}\.\d{2})\d\b', r'\1', text)

        # 4. Normalisasi tanda hubung untuk rentang
        text = re.sub(r'\s*--\s*', ' - ', text)
        text = re.sub(r'\s*-\s*', ' - ', text)

        # 5. Hapus tanda baca yang TIDAK ingin dipertahankan
        punctuation_to_keep = r"\.\/\-:,@"  # Escape karakter khusus regex
        text = re.sub(fr"[^\w\s{punctuation_to_keep}]", '', text)

        # 5. Hapus whitespace berlebih
        text = ' '.join(text.split())
        return text.strip()

    except Exception as e:
        logger.error(f"Error preprocessing text: {str(e)}")
        return text


def preprocess_text_for_ner(text):
    """
    Melakukan preprocessing pada teks hasil OCR untuk tugas NER.
    Fungsi ini mempertahankan tanda baca penting, huruf kapital, dan struktur
    yang relevan untuk pengenalan entitas.
    """
    if not isinstance(text, str):
        logger.warning("Input bukan string, mengembalikan input asli.")
        return text

    try:
        # 1. Normalisasi unicode (handle karakter khusus)
        text = unidecode(text)

        text = text.replace('\n', ' ')
        text = apply_rule_based_corrections(text)

        # 3. Menambahkan spasi antara huruf dan angka
        text = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', text)
        text = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', text)
        text = re.sub(r'(\d{2}\.\d{2})\d\b', r'\1', text)

        # 4. Normalisasi tanda hubung untuk rentang
        text = re.sub(r'\s*--\s*', ' - ', text)
        text = re.sub(r'\s*-\s*', ' - ', text)

        # 5. Hapus tanda baca yang TIDAK ingin dipertahankan
        punctuation_to_keep = r"\.\/\-:,@"  # Escape karakter khusus regex
        text = re.sub(fr"[^\w\s{punctuation_to_keep}]", '', text)

        # 5. Hapus whitespace berlebih
        text = ' '.join(text.split())
        return text.strip()

    except Exception as e:
        logger.error(f"Error preprocessing text: {str(e)}")
        return text


def intelligent_postprocessing(raw_ocr_text: str) -> dict:
    """
    Melakukan post-processing cerdas pada teks hasil OCR (dari PSM 6)
    untuk menghasilkan dua format output: satu untuk NER (menjaga struktur)
    dan satu untuk Klasifikasi (teks mengalir).

    Args:
        raw_ocr_text: String mentah hasil dari Pytesseract.

    Returns:
        Sebuah dictionary berisi:
        {
            "text_for_ner": "Teks yang bersih dengan struktur baris baru.",
            "text_for_classification": "Satu blok teks panjang tanpa baris baru."
        }
    """
    logger.info("Memulai intelligent post-processing...")

    text = apply_rule_based_corrections(raw_ocr_text)
    text = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', text)
    text = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', text)
    text = re.sub(r'(\d{2}\.\d{2})\d\b', r'\1', text)

    # 1. Pembersihan Awal (Universal)
    #    - Pisahkan teks menjadi baris-baris.
    #    - Hapus spasi di awal/akhir setiap baris.
    lines = text.strip().split('\n')
    cleaned_lines = [line.strip() for line in lines]

    #    - Hapus baris yang mungkin hanya berisi karakter non-alfanumerik atau terlalu pendek
    #      (seringkali merupakan noise dari OCR).
    meaningful_lines = []
    for line in cleaned_lines:
        # Menghapus spasi berlebih di dalam baris, misal "Kata   Satu" -> "Kata Satu"
        line = re.sub(r'\s+', ' ', line)

        # Hanya pertimbangkan baris yang memiliki setidaknya satu huruf atau angka.
        if re.search(r'[a-zA-Z0-9]', line):
            meaningful_lines.append(line)

    # 2. Pembuatan Teks untuk NER (Menjaga Struktur)
    #    - Gabungkan kembali baris-baris yang sudah bersih dengan satu baris baru.
    #    - Ini akan mempertahankan struktur vertikal dokumen.
    text_for_ner = "\n".join(meaningful_lines)
    logger.info("Teks untuk NER berhasil dibuat.")

    # 3. Pembuatan Teks untuk Klasifikasi (Menghancurkan Struktur)
    #    - Ambil teks yang sudah rapi untuk NER.
    #    - Ganti semua baris baru dengan satu spasi.
    text_for_classification = text_for_ner.replace('\n', ' ').strip()
    #    - Pastikan lagi tidak ada spasi ganda setelah penggabungan.
    text_for_classification = re.sub(r'\s+', ' ', text_for_classification)
    logger.info("Teks untuk Klasifikasi berhasil dibuat.")

    return {
        "text_for_ner": text_for_ner,
        "text_for_classification": text_for_classification
    }