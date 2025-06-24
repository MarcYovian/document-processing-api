import logging
import pprint
import re

import pandas as pd

from app.utils.similar import similar


def initialize_event_dict_v4():
    return {
        "nama_kegiatan_utama": "",
        "deskripsi_tambahan_kegiatan": [],
        "tanggal_kegiatan": [],
        "jam_kegiatan": [],
        "lokasi_kegiatan": [],
        "penanggung_jawab": [],
        "kontak_pj": [],
        "barang_dipinjam": [],
        "jumlah_peserta": [],
        "susunan_acara": [],
        "catatan_tambahan": [],
        "_last_entity_end": -1,  # Untuk melacak posisi akhir entitas terakhir yang ditambahkan
        "_has_key_details": False  # Untuk menandai jika event sudah punya detail kunci (tanggal/lokasi)
    }


def clean_jam_kegiatan(jam_str):  # Contoh fungsi pembersih jam (perlu disempurnakan)
    if not jam_str: return ""
    cleaned = re.sub(r'(\d{2})\.\s+(\d{2})', r'\1.\2', jam_str)
    cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
    cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned)
    cleaned = cleaned.replace(';', '').replace('..', '.').strip()
    if "wib" not in cleaned.lower():
        cleaned += " WIB"
    cleaned = cleaned.replace('- -', '-')
    # Anda mungkin perlu logika lebih untuk menangani "320 wib" atau format aneh lainnya
    return cleaned.strip()


def ekstrak_detail_kegiatan_v4(entities):
    daftar_kegiatan = []
    if not entities:
        return daftar_kegiatan

    # Pastikan entitas diurutkan berdasarkan posisi 'start'
    # Ini krusial untuk logika proximity dan urutan
    if isinstance(entities, pd.DataFrame):
        if 'start' not in entities.columns:
            logging.info("Peringatan: DataFrame untuk kegiatan tidak memiliki kolom 'start'. Hasil mungkin tidak akurat.")
            # Anda bisa mencoba mengembalikan list kosong atau memproses tanpa urutan (tidak disarankan)
            return []
        entities_sorted = entities.sort_values(by='start').to_dict(orient='records')
    elif isinstance(entities, list) and entities and isinstance(entities[0], dict) and 'start' in entities[0]:
        entities_sorted = sorted(entities, key=lambda x: x.get('start', 0))
    else:
        logging.error("Format input 'entities' untuk kegiatan tidak valid atau tidak memiliki 'start'.")
        return []

    pprint.pprint(entities_sorted)

    current_event = None
    MAX_ENTITY_GAP = 150  # Jarak karakter maksimal antar entitas dalam satu blok kegiatan (bisa disesuaikan)

    for i, entity in enumerate(entities_sorted):
        group = entity.get('entity_group')
        word = str(entity.get('word', '')).strip()
        start_pos = entity.get('start', 0)
        end_pos = entity.get('end', start_pos + len(word))  # Perkirakan end jika tidak ada

        # --- Logika Deteksi Awal Kegiatan Baru ---
        new_event_triggered = False
        if current_event is None:
            # Hanya mulai event baru jika entitasnya adalah EVT atau EVTDATE (atau EVTTIME/EVTLOC jika sangat awal)
            if group in ['EVT', 'EVTDATE'] or (
                    group in ['EVTTIME', 'EVTLOC'] and start_pos < 100):  # Asumsi <100 adalah awal dokumen
                new_event_triggered = True
        else:
            # 1. Pemicu berdasarkan jarak (gap)
            if start_pos - current_event["_last_entity_end"] > MAX_ENTITY_GAP:
                if group in ['EVT', 'EVTDATE', 'EVTTIME', 'EVTLOC']:  # Hanya jika entitas baru juga relevan untuk event
                    new_event_triggered = True

            # 2. Pemicu jika EVTDATE baru muncul dan event sebelumnya sudah punya detail kunci
            if not new_event_triggered and group == 'EVTDATE':
                if current_event.get("nama_kegiatan_utama") and current_event.get("_has_key_details"):
                    new_event_triggered = True

            # 3. Pemicu jika EVT baru muncul dan sangat berbeda dari nama event saat ini,
            #    DAN event saat ini sudah punya detail kunci (tanggal/lokasi)
            if not new_event_triggered and group == 'EVT':
                if current_event.get("nama_kegiatan_utama") and \
                        not similar(word, current_event["nama_kegiatan_utama"], threshold=0.65) and \
                        current_event.get("_has_key_details"):
                    new_event_triggered = True

        if new_event_triggered:
            if current_event and (
                    current_event["nama_kegiatan_utama"] or current_event["deskripsi_tambahan_kegiatan"] or
                    current_event["_has_key_details"]):
                daftar_kegiatan.append(current_event)
            current_event = initialize_event_dict_v4()

        if current_event is None: continue

        # --- Mengisi Detail ke current_event ---
        added_to_current_event = False
        if group == 'EVT':
            if not current_event["nama_kegiatan_utama"]:
                current_event["nama_kegiatan_utama"] = word
                added_to_current_event = True
            # Jika EVT baru mirip, dan mungkin lebih deskriptif, update nama utama
            elif similar(word, current_event["nama_kegiatan_utama"]):
                if len(word) > len(current_event["nama_kegiatan_utama"]):  # Ambil yang lebih panjang/spesifik
                    if current_event["nama_kegiatan_utama"] not in current_event[
                        "deskripsi_tambahan_kegiatan"]:  # Hindari duplikasi
                        current_event["deskripsi_tambahan_kegiatan"].append(current_event["nama_kegiatan_utama"])
                    current_event["nama_kegiatan_utama"] = word
                elif word.lower() != current_event["nama_kegiatan_utama"].lower() and \
                        word not in current_event["deskripsi_tambahan_kegiatan"]:
                    current_event["deskripsi_tambahan_kegiatan"].append(word)
                added_to_current_event = True
            # Jika EVT tidak mirip TAPI event saat ini belum punya detail kunci, mungkin ini masih bagian dari deskripsi
            elif not current_event["_has_key_details"] and word not in current_event["deskripsi_tambahan_kegiatan"]:
                current_event["deskripsi_tambahan_kegiatan"].append(word)
                added_to_current_event = True
            # Jika EVT tidak mirip DAN event sudah punya detail, ini seharusnya sudah ditangani oleh new_event_triggered
            # Jika tidak, maka ini masuk catatan tambahan
            elif word not in current_event["deskripsi_tambahan_kegiatan"]:
                current_event["catatan_tambahan"].append(f"{group}: {word}")
                added_to_current_event = True

        elif group == 'EVTDATE':
            current_event["tanggal_kegiatan"].append(word)
            current_event["_has_key_details"] = True
            added_to_current_event = True
        elif group == 'EVTTIME':
            current_event["jam_kegiatan"].append(clean_jam_kegiatan(word))  # Gunakan fungsi pembersih jam
            current_event["_has_key_details"] = True
            added_to_current_event = True
        elif group == 'EVTLOC':
            current_event["lokasi_kegiatan"].append({'name': word})
            current_event["_has_key_details"] = True
            added_to_current_event = True
        elif group == 'PER':
            current_event["penanggung_jawab"].append(word)
            added_to_current_event = True
        elif group == 'PHONE':
            current_event["kontak_pj"].append(word)
            added_to_current_event = True
        elif group == 'SCHEDULE_ITEM':
            current_event["susunan_acara"].append(word)
            added_to_current_event = True
        elif group == 'ITEM':
            jumlah_item = 1
            if i + 1 < len(entities_sorted) and entities_sorted[i + 1].get('entity_group') == 'ITEMQTY':
                try:
                    qty_word = str(entities_sorted[i + 1].get('word'))
                    qty_match = re.search(r'\d+', qty_word)
                    if qty_match:
                        jumlah_item = int(qty_match.group(0))
                except (ValueError, TypeError):
                    pass
            current_event["barang_dipinjam"].append({"item": word, "jumlah": jumlah_item})
            added_to_current_event = True
        elif group == 'PEOQTY':
            current_event["jumlah_peserta"].append(str(word))  # Sudah dibersihkan di basic_post_process
            added_to_current_event = True
        elif group not in ['DOCNUM', 'DOCDATE', 'CITY', 'SUBJECT', 'RECIPIENT', 'EMAIL', 'POSITION', 'ORG']:
            current_event["catatan_tambahan"].append(f"{group}: {word}")
            added_to_current_event = True

        if added_to_current_event:
            current_event["_last_entity_end"] = end_pos

    if current_event and (
            current_event["nama_kegiatan_utama"] or current_event["deskripsi_tambahan_kegiatan"] or current_event[
        "_has_key_details"]):
        daftar_kegiatan.append(current_event)

    # Pembersihan akhir
    for keg in daftar_kegiatan:
        if not keg["nama_kegiatan_utama"] and keg["deskripsi_tambahan_kegiatan"]:
            keg["nama_kegiatan_utama"] = "; ".join(sorted(list(set(keg["deskripsi_tambahan_kegiatan"]))))

        for key in list(keg.keys()):  # list(keg.keys()) untuk iterasi pada salinan kunci
            if key.startswith("_"):  # Hapus field internal
                del keg[key]
                continue

            if key in ["barang_dipinjam", "lokasi_kegiatan"]:
                # Logika khusus untuk lokasi_kegiatan
                if key == "lokasi_kegiatan":
                    all_locations = keg.get(key, [])
                    if not all_locations:
                        keg[key] = ""
                        continue
                    best_location_name = ""
                    for loc_dict in all_locations:
                        current_name = loc_dict.get("name", "")
                        if len(current_name) > len(best_location_name):
                            best_location_name = current_name
                    keg[key] = best_location_name
                continue

            if key == "susunan_acara":
                str_val_list = [str(val).strip() for val in keg[key] if str(val).strip()]
                unique_ordered_list = []
                if str_val_list:
                    seen_vals = set()
                    for item_val in str_val_list:
                        if item_val not in seen_vals:
                            unique_ordered_list.append(item_val)
                            seen_vals.add(item_val)
                # Simpan sebagai list (array), bukan string
                keg[key] = unique_ordered_list
                continue  # Lanjut ke key berikutnya

            if isinstance(keg[key], list):
                str_val_list = [str(val).strip() for val in keg[key] if str(val).strip()]
                unique_ordered_list = []
                if str_val_list:
                    seen_vals = set()
                    for item_val in str_val_list:
                        if item_val not in seen_vals:
                            unique_ordered_list.append(item_val)
                            seen_vals.add(item_val)
                keg[key] = "; ".join(unique_ordered_list)

            if not keg.get(key) and key in ["penanggung_jawab", "kontak_pj", "jumlah_peserta",
                                            "deskripsi_tambahan_kegiatan", "catatan_tambahan", "susunan_acara"]:
                keg[key] = ""  # Atau "Tidak disebutkan" jika lebih disukai

    return [keg for keg in daftar_kegiatan if keg.get("nama_kegiatan_utama")]