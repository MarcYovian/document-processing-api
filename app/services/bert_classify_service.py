import os

from transformers import pipeline

from core.config import settings


class BERTClassifyService:
    def __init__(self):
        try:
            model_path = settings.CLASSIFY_MODEL
            self.classifier = pipeline(
                "text-classification",
                model=model_path,
                tokenizer=model_path
            )

            print(f"Model BERT '{settings.CLASSIFY_MODEL}' berhasil dimuat.")
        except Exception as e:
            print(f"Error saat memuat model BERT: {e}")
            self.classifier = None

    def classify_text(self, text: str):
        if not self.classifier:
            return "Error: Model BERT tidak berhasil dimuat."

        try:
            result = self.classifier(text)
            return result
        except Exception as e:
            return f"Error Classify: {e}"
