import logging
import pprint

import pandas as pd


def ekstrak_blok_penanda_tangan_v3(entities_input_list):  # Ganti nama fungsi jika perlu
    """
    Mengekstrak blok penanda tangan dengan mencoba memisahkan pasangan jabatan-nama
    yang berbeda dalam satu blok visual.
    """
    penanda_tangan_final = []
    sisa_entitas_final = []  # Entitas yang tidak masuk ke blok tanda tangan

    if not entities_input_list:
        return [], []

    # Pastikan format input dan pengurutan
    entities_sorted = []
    try:
        if isinstance(entities_input_list, list) and entities_input_list and isinstance(entities_input_list[0],
                                                                                        dict) and 'start' in \
                entities_input_list[0]:
            entities_sorted = sorted(entities_input_list, key=lambda x: x.get('start', 0))
        elif isinstance(entities_input_list, pd.DataFrame):
            if 'start' in entities_input_list.columns:
                entities_sorted = entities_input_list.sort_values(by='start').to_dict(orient='records')
            else:
                logging.info("Peringatan: DataFrame (blok ttd) tidak memiliki kolom 'start'.")
                entities_sorted = entities_input_list.to_dict(orient='records')
        else:
            logging.info("Peringatan: Format input (blok ttd) tidak dikenal untuk pengurutan.")
            entities_sorted = list(entities_input_list)
    except Exception as e:
        logging.error(f"Error saat persiapan entitas di ekstrak_blok_penanda_tangan: {e}.")
        entities_sorted = list(entities_input_list)

    indices_terpakai_untuk_ttd = set()
    i = 0
    while i < len(entities_sorted):
        if i in indices_terpakai_untuk_ttd:
            i += 1
            continue

        current_entity = entities_sorted[i]

        # Hanya mulai proses jika menemukan POSITION yang belum terpakai
        if current_entity.get('entity_group') == 'POSITION':

            # Langkah 1: Kumpulkan blok JABATAN
            list_jabatan_parts = []
            last_pos_idx = -1
            temp_j = i
            while temp_j < len(entities_sorted) and entities_sorted[temp_j].get('entity_group') == 'POSITION':
                if temp_j > i and (
                        entities_sorted[temp_j].get('start', 0) - entities_sorted[temp_j - 1].get('end', 0)) > 15:
                    break
                list_jabatan_parts.append(str(entities_sorted[temp_j].get('word', '')))
                last_pos_idx = temp_j
                temp_j += 1

            # Langkah 2: Kumpulkan blok NAMA
            list_nama_parts = []
            last_per_idx = -1
            temp_p = temp_j
            while temp_p < len(entities_sorted) and entities_sorted[temp_p].get('entity_group') == 'PER':
                is_first_per = (temp_p == temp_j)
                if is_first_per and (
                        entities_sorted[temp_p].get('start', 0) - entities_sorted[last_pos_idx].get('end', 0)) > 75:
                    break
                if not is_first_per and (
                        entities_sorted[temp_p].get('start', 0) - entities_sorted[temp_p - 1].get('end', 0)) > 15:
                    break

                list_nama_parts.append(str(entities_sorted[temp_p].get('word', '')))
                last_per_idx = temp_p
                temp_p += 1

            # === LANGKAH 3: Logika Hibrida untuk Memproses Pasangan ===
            if list_jabatan_parts and list_nama_parts:

                # KASUS SPESIAL: Jika jumlah jabatan sama dengan jumlah nama (untuk layout bersebelahan)
                if len(list_jabatan_parts) == len(list_nama_parts) and len(list_jabatan_parts) > 1:
                    for j_idx in range(len(list_jabatan_parts)):
                        penanda_tangan_final.append({
                            "jabatan": list_jabatan_parts[j_idx].strip(),
                            "nama": list_nama_parts[j_idx].strip()
                        })
                # KASUS UMUM: Satu penanda tangan (bisa dengan jabatan/nama multi-kata)
                else:
                    jabatan_final = " ".join(list_jabatan_parts).strip()
                    nama_final = " ".join(list_nama_parts).strip()
                    penanda_tangan_final.append({"jabatan": jabatan_final, "nama": nama_final})

                # Tandai semua indeks sebagai terpakai
                for k_idx in range(i, last_per_idx + 1):
                    indices_terpakai_untuk_ttd.add(k_idx)

                i = last_per_idx + 1
                continue

        # Jika bukan 'POSITION' atau tidak ditemukan pasangan, lanjut ke entitas berikutnya
        i += 1

    # Kumpulkan sisa entitas
    for k_idx in range(len(entities_sorted)):
        if k_idx not in indices_terpakai_untuk_ttd:
            sisa_entitas_final.append(entities_sorted[k_idx])

    return penanda_tangan_final, sisa_entitas_final