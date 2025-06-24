import logging
import pprint
import re

import pandas as pd


def ekstrak_info_umum(entities_input_list):
    """
    Mengekstrak informasi umum dokumen dan mengembalikan sisa entitas.
    """
    info_umum_dokumen = {
        "nomor_surat": [], "tanggal_surat_dokumen": [], "kota_surat": [],
        "perihal_surat": [], "penerima_surat": [], "email_pengirim": [],
        "organisasi": []
    }

    sisa_entitas = []

    if not entities_input_list:
        return info_umum_dokumen, sisa_entitas

    # Pastikan kita bekerja dengan list of dictionaries dan sudah terurut berdasarkan 'start'
    try:
        if isinstance(entities_input_list, list) and entities_input_list and isinstance(entities_input_list[0],
                                                                                        dict) and 'start' in \
                entities_input_list[0]:
            entities_sorted = sorted(entities_input_list, key=lambda x: x.get('start', 0))
        elif isinstance(entities_input_list, pd.DataFrame):
            if 'start' in entities_input_list.columns:
                entities_sorted = entities_input_list.sort_values(by='start').to_dict(orient='records')
            else:
                logging.info("Peringatan: DataFrame (info umum) tidak memiliki kolom 'start'. Memproses apa adanya.")
                entities_sorted = entities_input_list.to_dict(orient='records')
        else:
            # Jika bukan list of dict atau DataFrame, coba iterasi langsung
            # Ini mungkin perlu penyesuaian lebih lanjut tergantung tipe data sebenarnya
            logging.info(
                "Peringatan: Format input entities_input_list (info umum) tidak dikenal untuk pengurutan. Memproses "
                "apa adanya.")
            entities_sorted = list(entities_input_list)
    except Exception as e:
        logging.error(f"Error saat persiapan entitas di ekstrak_info_umum: {e}. Menggunakan input list apa adanya.")
        entities_sorted = list(entities_input_list)

    end_zone_start_threshold = 0
    if entities_sorted:
        # Ambil posisi start dari entitas terakhir sebagai referensi panjang dokumen
        last_entity_start_pos = entities_sorted[-1].get('start', 0)
        # Tentukan titik awal "zona akhir" (misal, 60% dari panjang total)
        end_zone_start_threshold = last_entity_start_pos * 0.6

    # Kumpulan entitas yang sudah diproses untuk info umum (indeksnya)
    indeks_entitas_info_umum = set()
    for i, entity in enumerate(entities_sorted):
        group = entity.get('entity_group')
        word = str(entity.get('word', ''))
        start_pos = entity.get('start', 0)  # Posisi awal entitas

        entitas_diproses_untuk_info_umum = False

        if group == 'ORG':
            info_umum_dokumen["organisasi"].append(word)
            entitas_diproses_untuk_info_umum = True
        elif group == 'DOCNUM':
            info_umum_dokumen["nomor_surat"].append(word)
            entitas_diproses_untuk_info_umum = True
        elif group == 'DOCDATE':
            if start_pos < 200 or start_pos > end_zone_start_threshold:
                info_umum_dokumen["tanggal_surat_dokumen"].append(word)
                entitas_diproses_untuk_info_umum = True
        elif group == 'CITY':  # Asumsi kota surat di awal
            is_in_header = start_pos < 200
            is_in_signature_zone = start_pos > end_zone_start_threshold

            # Cek apakah entitas berikutnya adalah DOCDATE
            is_followed_by_docdate = False
            if i + 1 < len(entities_sorted):  # Pastikan ada entitas berikutnya
                next_entity = entities_sorted[i + 1]
                if next_entity.get('entity_group') == 'DOCDATE':
                    is_followed_by_docdate = True

            # Kondisi: Valid jika di header, ATAU di zona akhir, ATAU diikuti oleh tanggal
            if is_in_header or is_in_signature_zone or is_followed_by_docdate:
                info_umum_dokumen["kota_surat"].append(word)
                entitas_diproses_untuk_info_umum = True
        elif group == 'SUBJECT':
            info_umum_dokumen["perihal_surat"].append(word)
            entitas_diproses_untuk_info_umum = True
        elif group == 'RECIPIENT':
            pos_word = ""  # Inisialisasi dengan nilai default
            if i + 1 < len(entities_sorted) and entities_sorted[i + 1].get('entity_group') == 'RECIPIENT_POSITION':
                try:
                    pos_word = entities_sorted[i + 1].get('word')
                except (ValueError, TypeError):
                    pass
            else:
                pos_word = ""
            info_umum_dokumen["penerima_surat"].append({"name": word, "position": pos_word})
            # info_umum_dokumen["penerima_surat"].append(word)
            entitas_diproses_untuk_info_umum = True
        elif group == 'EMAIL' and start_pos < 200:  # Asumsi email pengirim di awal
            info_umum_dokumen["email_pengirim"].append(word)
            entitas_diproses_untuk_info_umum = True

        if entitas_diproses_untuk_info_umum:
            indeks_entitas_info_umum.add(i)  # Tandai indeks entitas ini sudah dipakai

    # Format ulang nilai di info_umum_dokumen (join list menjadi string)
    for key, val_list in info_umum_dokumen.items():
        unique_ordered = []
        if val_list:
            seen = set()
            for item in val_list:
                item_str = str(item).strip()
                if item_str not in seen:
                    seen.add(item_str)
                    unique_ordered.append(item_str)

        if key == "nomor_surat" and unique_ordered:
            if len(unique_ordered) == 1:
                full_doc_num = unique_ordered[0]
            else:
                processed_parts = []
                for k_part_idx, part_str in enumerate(unique_ordered):
                    cleaned_inner_part = "/".join([seg.strip() for seg in part_str.split('/')])
                    if k_part_idx == 0:
                        processed_parts.append(cleaned_inner_part)
                    else:
                        prev_part = processed_parts[-1]
                        if prev_part.endswith('/'):
                            if cleaned_inner_part.startswith('/'):
                                processed_parts.append(cleaned_inner_part[1:])
                            else:
                                processed_parts.append(cleaned_inner_part)
                        elif not cleaned_inner_part.startswith('/'):
                            processed_parts.append('/')
                            processed_parts.append(cleaned_inner_part)
                        else:
                            processed_parts.append(cleaned_inner_part)
                full_doc_num = "".join(processed_parts)

            full_doc_num = re.sub(r'\s*/\s*', '/', full_doc_num)
            full_doc_num = re.sub(r'/+', '/', full_doc_num)
            info_umum_dokumen[key] = full_doc_num
        elif key == "penerima_surat":
            continue
        elif key == "organisasi":
            info_umum_dokumen[key] = [{'nama': org} for org in unique_ordered] if unique_ordered else []
        elif unique_ordered:
            if key in ["tanggal_surat_dokumen", "kota_surat"]:
                info_umum_dokumen[key] = unique_ordered[0]
            else:
                info_umum_dokumen[key] = "; ".join(unique_ordered)
        else:
            info_umum_dokumen[key] = ""

    for i, entity in enumerate(entities_sorted):
        if i not in indeks_entitas_info_umum:
            sisa_entitas.append(entity)

    return info_umum_dokumen, sisa_entitas
