import logging
import os

from transformers import pipeline

from core.config import settings


class BERTNERService:
    def __init__(self):
        try:
            model_path = settings.NER_MODEL
            self.ner_pipeline = pipeline(
                "ner",
                model=model_path,
                tokenizer=model_path,
                aggregation_strategy="first"
            )

            logging.info(f"Model BERT '{settings.NER_MODEL}' berhasil dimuat.")
        except Exception as e:
            logging.error(f"Error saat memuat model BERT: {e}")
            self.ner_pipeline = None

    def extract_text(self, text: str):
        if not self.ner_pipeline:
            return "Error: Model BERT tidak berhasil dimuat."

        try:
            result = self.ner_pipeline(text)
            return result
        except Exception as e:
            return f"Error Extract: {e}"
