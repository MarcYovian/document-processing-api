import logging
from typing import List, Dict, Any

from transformers import Pipeline, pipeline


class NERError(Exception):
    """Base exception class untuk semua error terkait NER."""
    pass


class ModelLoadError(NERError):
    """Dilemparkan ketika model NER dari Hugging Face gagal dimuat."""
    pass


# --- Logger ---
logger = logging.getLogger(__name__)


class NERService:
    """
    Kelas yang bertanggung jawab untuk memuat model NER, melakukan prediksi,
    dan mengelompokkan entitas.
    """
    def __init__(self, model_name_or_path: str):
        """
        Inisialisasi service dengan memuat pipeline token-classification (NER).

        Args:
            model_name_or_path: Nama model atau path lokal ke model di Hugging Face.
        """
        self.model_name = model_name_or_path
        self.ner_pipeline: Pipeline = None
        try:
            logger.info(f"Mencoba memuat model NER: {self.model_name}...")
            self.ner_pipeline = pipeline(
                "ner",
                model=self.model_name,
                tokenizer=self.model_name,
                aggregation_strategy="first"
            )
            logger.info(f"Model NER '{self.model_name}' berhasil dimuat.")
        except Exception as e:
            logger.critical(f"Gagal memuat model NER '{self.model_name}'. Error: {e}", exc_info=True)
            raise ModelLoadError(f"Gagal memuat model NER: {e}")

    def predict_entities_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Melakukan ekstraksi entitas dari sebuah teks.

        Args:
            text: Teks yang akan diekstraksi entitasnya (format "text_for_ner").

        Returns:
            Sebuah list berisi dictionary entitas yang ditemukan.
            Contoh: [{'entity_group': 'PER', 'score': 0.99, 'word': 'Valentina Yudistia'}]

        Raises:
            NERError: Jika terjadi error selama proses prediksi.
        """
        if not self.ner_pipeline:
            logger.error("Model NER tidak dimuat, tidak dapat melakukan prediksi.")
            raise NERError("Model NER tidak tersedia.")

        if not text or not isinstance(text, str) or not text.strip():
            logger.warning("Mencoba melakukan ekstraksi entitas pada teks kosong atau tidak valid.")
            return []

        try:
            logger.info("Melakukan prediksi ekstraksi entitas...")
            entities = self.ner_pipeline(text)
            logger.info(f"Ekstraksi entitas berhasil, ditemukan {len(entities)} entitas.")
            return entities
        except Exception as e:
            logger.error(f"Terjadi error saat melakukan ekstraksi entitas: {e}", exc_info=True)
            raise NERError(f"Terjadi error internal saat prediksi entitas: {e}")