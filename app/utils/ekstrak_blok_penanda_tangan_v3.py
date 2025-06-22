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
                print("Peringatan: DataFrame (blok ttd) tidak memiliki kolom 'start'.")
                entities_sorted = entities_input_list.to_dict(orient='records')
        else:
            print("Peringatan: Format input (blok ttd) tidak dikenal untuk pengurutan.")
            entities_sorted = list(entities_input_list)
    except Exception as e:
        print(f"Error saat persiapan entitas di ekstrak_blok_penanda_tangan: {e}.")
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
            list_jabatan_parts = []
            last_pos_idx = -1

            # 1. Kumpulkan bagian-bagian untuk satu jabatan logis
            temp_j = i
            while temp_j < len(entities_sorted) and \
                    temp_j not in indices_terpakai_untuk_ttd and \
                    entities_sorted[temp_j].get('entity_group') == 'POSITION':
                # Heuristik kedekatan untuk jabatan multi-kata
                if temp_j > i and (entities_sorted[temp_j].get('start', 0) - entities_sorted[temp_j - 1].get('end',
                                                                                                             float('-inf'))) > 15:  # Gap yang lebih besar menandakan jabatan baru
                    break
                list_jabatan_parts.append(str(entities_sorted[temp_j].get('word', '')))
                last_pos_idx = temp_j
                temp_j += 1

            if not list_jabatan_parts:  # Seharusnya tidak terjadi
                i += 1
                continue

            # `temp_j` sekarang menunjuk ke entitas pertama setelah blok POSITION ini

            # 2. Cari blok PER yang mengikuti LANGSUNG setelah blok POSITION ini
            list_nama_parts = []
            last_per_idx = -1
            temp_p = temp_j  # Mulai dari setelah blok POSITION

            while temp_p < len(entities_sorted) and \
                    temp_p not in indices_terpakai_untuk_ttd and \
                    entities_sorted[temp_p].get('entity_group') == 'PER':
                # Heuristik kedekatan untuk nama multi-kata
                # Jika ini PER pertama setelah POSITION, atau PER berikutnya dekat dengan PER sebelumnya
                is_first_per_after_position = (temp_p == temp_j)
                is_subsequent_per_close_enough = (temp_p > temp_j) and \
                                                 (entities_sorted[temp_p].get('start', 0) - entities_sorted[
                                                     temp_p - 1].get('end', float('-inf'))) <= 15

                if is_first_per_after_position or is_subsequent_per_close_enough:
                    # Cek juga jarak dari POSITION terakhir ke PER pertama
                    if is_first_per_after_position and \
                            (entities_sorted[temp_p].get('start', 0) - entities_sorted[last_pos_idx].get('end', float(
                                '-inf'))) > 30:  # Gap besar antara jabatan dan nama
                        break  # Mungkin bukan pasangan langsung

                    list_nama_parts.append(str(entities_sorted[temp_p].get('word', '')))
                    last_per_idx = temp_p
                    temp_p += 1
                else:
                    break  # PER tidak cukup dekat, bukan bagian dari nama ini

            if list_nama_parts:  # Jika pasangan Jabatan dan Nama ditemukan
                if len(list_jabatan_parts) > 0 and len(list_nama_parts) > 0:
                    # Jika jumlahnya sama dan > 1, coba pasangkan satu-satu
                    if len(list_jabatan_parts) == len(list_nama_parts) and len(list_jabatan_parts) > 1:
                        for j_idx in range(len(list_jabatan_parts)):
                            penanda_tangan_final.append({
                                "jabatan": list_jabatan_parts[j_idx].strip(),
                                "nama": list_nama_parts[j_idx].strip()
                            })
                    else:  # Kasus umum: satu blok jabatan, satu blok nama (bisa multi-token)
                        jabatan_final = " ".join(list_jabatan_parts).strip()
                        nama_final = " ".join(list_nama_parts).strip()
                        penanda_tangan_final.append({"jabatan": jabatan_final, "nama": nama_final})

                    for k_idx in range(i, last_per_idx + 1):
                        indices_terpakai_untuk_ttd.add(k_idx)
                    i = last_per_idx + 1
                    continue
            else:
                # Tidak ditemukan PER yang cocok untuk blok POSITION ini
                # Biarkan POSITION ini masuk ke sisa_entitas (tidak di-increment i secara khusus di sini)
                pass

        i += 1  # Lanjut ke entitas berikutnya jika tidak ada blok ttd yang valid dimulai di i

    # Kumpulkan sisa entitas
    for k_idx in range(len(entities_sorted)):
        if k_idx not in indices_terpakai_untuk_ttd:
            sisa_entitas_final.append(entities_sorted[k_idx])

    return sisa_entitas_final, penanda_tangan_final