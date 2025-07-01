import logging
from typing import List, Dict, Any

from transformers import pipeline, Pipeline

from ..core.config import settings


class ClassifierError(Exception):
    """Base exception class untuk semua error terkait klasifikasi."""
    pass

class ModelLoadError(ClassifierError):
    """Dilemparkan ketika model klasifikasi dari Hugging Face gagal dimuat."""
    pass


logger = logging.getLogger(__name__)


class TextClassifierService:
    def __init__(self, model_name_or_path: str):
        """
        Inisialisasi service dengan memuat pipeline klasifikasi dari Hugging Face.

        Args:
            model_name_or_path: Nama model atau path lokal ke model di Hugging Face.
        """
        self.model_name = model_name_or_path
        self.classifier: Pipeline = None
        try:
            logger.info(f"Mencoba memuat model klasifikasi: {self.model_name}...")
            model_path = settings.CLASSIFY_MODEL
            self.classifier = pipeline(
                "text-classification",
                model=model_path,
                tokenizer=model_path
            )

            logger.info(f"Model klasifikasi '{settings.CLASSIFY_MODEL}' berhasil dimuat.")
        except Exception as e:
            logger.critical(f"Gagal memuat model klasifikasi '{self.model_name}'. Error: {e}", exc_info=True)
            raise ModelLoadError(f"Gagal memuat model klasifikasi: {e}")

    def classify_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Melakukan klasifikasi pada sebuah teks.

        Args:
            text: Teks yang akan diklasifikasi (idealnya, format "text_for_classification").

        Returns:
            Sebuah list berisi dictionary hasil prediksi, contoh: [{'label': 'SURAT_PERMOHONAN', 'score': 0.99...}]

        Raises:
            ClassifierError: Jika terjadi error selama proses prediksi.
        """
        if not self.classifier:
            logger.error("Model klasifikasi tidak dimuat, tidak dapat melakukan prediksi.")
            raise ClassifierError("Model klasifikasi tidak tersedia.")

        if not text or not isinstance(text, str) or not text.strip():
            logger.warning("Mencoba melakukan klasifikasi pada teks kosong atau tidak valid.")
            return []

        try:
            logger.info("Melakukan prediksi klasifikasi...")
            result = self.classifier(text, truncation=True)
            logger.info(f"Prediksi berhasil: {result}")
            return result
        except Exception as e:
            logger.error(f"Terjadi error saat melakukan klasifikasi: {e}", exc_info=True)
            raise ClassifierError(f"Terjadi error internal saat prediksi: {e}")