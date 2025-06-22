import re
from unidecode import unidecode
import logging


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
        r"\bGriva\b": "Griya",
        r'\b(No|Hal|Lampiran|Perihal)l-': r'\1: -',
        r'\b(No|Hal|Lampiran|Perihal)\s*l-': r'\1: -',
        r'\b(No|Hal|Lampiran|Perihal)\s*--\s*:-': r'\1: -',
        r'\b/II1/\b': '/III/',
        r'\b/I1/\b': '/II/',
        r'\b/111/\b': '/III/',
        r'\b/vii\s*1\b': '/VIII',
        r'\b/V1/\b': '/VI/',
        r'/\s*FEBRUARI\s*1\s*/': '/FEBRUARI/',
        r"\b\s*GPILANG\s*\b": " KARANGPILANG ",
        r"\s*SU\s*AYA\s*": " SURABAYA ",
        r"\b\bYth\s*\.\s*\b": "Yth. ",
        r"\bYik\s*\.\s*": "Ytk. ",
        r"\bYtih\s*\.\s*": "Yth. ",
        r"\bYith\s*\.\s*": "Yth. ",
        r"\bN0\b": "No",
        r"\s*-\s*:": " :",
        r'\bl\.': '1.',
        r'\bI\b': '',
        r'\bl\b': '',
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
            logging.warning(f"Pola regex tidak valid '{pattern}': {e}")

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
        logging.error(f"Error preprocessing text: {str(e)}")
        return text
