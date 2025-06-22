from app.utils.basic_post_process_entities import basic_post_process_entities
from app.utils.ekstrak_blok_penanda_tangan_v3 import ekstrak_blok_penanda_tangan_v3
from app.utils.ekstrak_detail_kegiatan_v4 import ekstrak_detail_kegiatan_v4
from app.utils.ekstrak_info_umum import ekstrak_info_umum


def strukturkan_dokumen_lengkap(ner_pipeline_output_list, file_name_asli, teks_dokumen_asli, type):
    """Fungsi utama untuk memproses dari output pipeline ke JSON terstruktur."""
    if not ner_pipeline_output_list:
        # ... (penanganan jika tidak ada entitas) ...
        return {  # kembalikan struktur kosong
            "type": type,
            "nama_file_sumber": file_name_asli,
            "teks_dokumen_asli": teks_dokumen_asli,
            "informasi_umum_dokumen": {},
            "detail_kegiatan": [],
            "blok_penanda_tangan": []
        }

    entities_processed_basic = basic_post_process_entities(ner_pipeline_output_list)
    if not entities_processed_basic:
        # ... (penanganan jika tidak ada entitas setelah post-processing dasar) ...
        return {  # kembalikan struktur kosong
            "type": type,
            "nama_file_sumber": file_name_asli,
            "teks_dokumen_asli": teks_dokumen_asli,
            "informasi_umum_dokumen": {},
            "detail_kegiatan": [],
            "blok_penanda_tangan": []
        }

    # 1. Ekstrak Informasi Umum DAN dapatkan sisa entitas
    info_umum, entitas_setelah_info_umum = ekstrak_info_umum(entities_processed_basic)

    # 2. Ekstrak Blok Penanda Tangan dari entitas_setelah_info_umum
    sisa_entitas_setelah_ttd, blok_penanda_tangan = ekstrak_blok_penanda_tangan_v3(entitas_setelah_info_umum)

    # 3. Ekstrak Detail Kegiatan dari sisa_entitas_setelah_ttd
    detail_kegiatan = ekstrak_detail_kegiatan_v4(sisa_entitas_setelah_ttd)

    hasil_final_json = {
        "type": type,
        "nama_file_sumber": file_name_asli,
        "informasi_umum_dokumen": info_umum,
        "detail_kegiatan": detail_kegiatan,
        "blok_penanda_tangan": blok_penanda_tangan
    }
    return hasil_final_json
