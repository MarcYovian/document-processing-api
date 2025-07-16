import logging
from typing import List, Dict, Any

import pandas as pd

from src.document_api.utils.extract_document_info import extract_document_info
from src.document_api.utils.extract_signature_blocks import extract_signature_blocks
from src.document_api.utils.extract_structured_events import extract_structured_events

logger = logging.getLogger(__name__)


class InformationExtractionService:
    """
    Kelas yang bertanggung jawab untuk mengekstrak informasi terstruktur
    dari hasil OCR dan prediksi NER.
    """

    def __init__(self):
        logger.info("InformationExtractionService diinisialisasi.")

    def process_extraction(
            self,
            classification: str,
            text_for_ner: str,
            entities: List[Dict],
            filename: str
    ) -> dict[str, str | list[Any] | dict[Any, Any]]:
        """
        Fungsi utama yang mengarahkan ke metode ekstraksi yang tepat
        berdasarkan hasil klasifikasi dokumen.
        """
        if not entities:
            # ... (penanganan jika tidak ada entitas) ...
            return {
                "type": classification,
                "file_name": filename,
                "text": text_for_ner,
                "document_information": {},
                "events": [],
                "signature_blocks": []
            }

        processed_entities = []
        for entity in entities:
            new_entity = entity.copy()  # Hindari modifikasi list asli
            if "start" in new_entity and "end" in new_entity:
                entity_text = text_for_ner[new_entity["start"]:new_entity["end"]]
                new_entity["entity_text"] = entity_text.replace('\n', ' ')
            processed_entities.append(new_entity)

        info, remaining_entities = extract_document_info(processed_entities)
        signature_blocks, remaining_entities = extract_signature_blocks(remaining_entities)
        events = extract_structured_events(remaining_entities)

        data = {
            "type": classification,
            "file_name": filename,
            "text": text_for_ner,
            "document_information": info,
            "events": events,
            "signature_blocks": signature_blocks
        }

        return data


