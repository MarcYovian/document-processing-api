import logging
from typing import List, Dict, Any

from src.document_api.utils.strukturkan_dokumen_lengkap import strukturkan_dokumen_lengkap

logger = logging.getLogger(__name__)


class InformationExtractionService:
    """
    Kelas yang bertanggung jawab untuk mengekstrak informasi terstruktur
    dari hasil OCR dan prediksi NER.
    """

    def __init__(self):
        logger.info("InformationExtractionService diinisialisasi.")

    def process_extraction(self, classification: str, text_for_ner: str, entities: List[Dict], filename: str) -> List[Dict[str, Any]]:
        """
        Fungsi utama yang mengarahkan ke metode ekstraksi yang tepat
        berdasarkan hasil klasifikasi dokumen.
        """
        data = strukturkan_dokumen_lengkap(
            ner_pipeline_output_list=entities,
            file_name_asli=filename,
            teks_dokumen_asli=text_for_ner,
            type=classification
        )
        return data
