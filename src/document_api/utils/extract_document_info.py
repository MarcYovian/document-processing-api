import re
from typing import List, Dict, Any, Tuple


def _clean_text(text: str) -> str:
    """Membersihkan teks dari spasi berlebih dan karakter tidak penting."""
    return re.sub(r'\s+', ' ', text).strip()


def _find_nearby_entity(
        base_entity: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        processed_indices: set,
        max_distance: int = 50
) -> Dict[str, Any] | None:
    """Mencari entitas kandidat terdekat yang belum diproses."""
    closest_candidate = None
    min_dist = float('inf')

    for candidate in candidates:
        if candidate['start'] in processed_indices:
            continue

        # Cari kandidat setelah entitas dasar
        if candidate['start'] >= base_entity['end']:
            dist = candidate['start'] - base_entity['end']
            if dist < min_dist and dist < max_distance:
                min_dist = dist
                closest_candidate = candidate

    return closest_candidate


def extract_document_info(
        entities: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Mengekstrak informasi umum dari daftar entitas dengan logika kontekstual
    dan mengembalikan output berstandar API (snake_case).

    Args:
        entities: Daftar entitas yang sudah diurutkan berdasarkan posisi 'start'.

    Returns:
        Tuple berisi (informasi umum dokumen, sisa entitas yang tidak terpakai).
    """
    if not entities:
        return {}, []

    # Standarisasi kunci input dari 'entity_text' atau 'word' ke 'text'
    standardized_entities = []
    for entity in entities:
        entity['text'] = entity.get('entity_text', '') or entity.get('word')
        standardized_entities.append(entity)

    entities_sorted = sorted(standardized_entities, key=lambda x: x.get('start', 0))

    info = {
        "document_number": None,
        "document_date": None,
        "document_city": None,
        "subjects": [],
        "recipients": [],
        "emitter_email": None,
        "emitter_organizations": []
    }

    processed_indices = set()

    # --- Identifikasi Kontekstual ---
    # Tentukan zona header berdasarkan posisi entitas ORG, DOCNUM, DOCDATE, CITY pertama
    first_metadata_pos = float('inf')
    for ent in entities_sorted:
        if ent['entity_group'] in ['ORG', 'DOCNUM', 'DOCDATE', 'CITY', 'SUBJECT', 'RECIPIENT']:
            first_metadata_pos = min(first_metadata_pos, ent['start'])
            break

    # 1. Proses entitas dengan prioritas tinggi (Nomor, Perihal, Email)
    for i, entity in enumerate(entities_sorted):
        group = entity['entity_group']
        text = _clean_text(entity['text'])

        if group == 'DOCNUM':
            info['document_number'] = text
            processed_indices.add(i)
        elif group == 'SUBJECT':
            info['subjects'].append(text)
            processed_indices.add(i)
        elif group == 'EMAIL' and entity['start'] < 300:  # Asumsi email di bagian atas
            info['emitter_email'] = text
            processed_indices.add(i)
        elif group == 'ORG':
            # Asumsikan ORG di awal adalah milik pengirim
            if entity['start'] < first_metadata_pos + 150:
                info['emitter_organizations'].append({"name": text})
                processed_indices.add(i)

    # 2. Proses Penerima (Recipient)
    # Kelompokkan dulu RECIPIENT dan RECIPIENT_POSITION
    all_recipients = [(i, e) for i, e in enumerate(entities_sorted) if
                      e['entity_group'] == 'RECIPIENT' and i not in processed_indices]
    all_positions = [e for e in entities_sorted if e['entity_group'] == 'RECIPIENT_POSITION']

    for i, recipient_entity in all_recipients:
        position_entity = _find_nearby_entity(recipient_entity, all_positions, processed_indices)

        position_text = ""
        if position_entity:
            position_text = _clean_text(position_entity['text'])
            # Tandai posisi yang sudah terpakai
            pos_index = entities_sorted.index(position_entity)
            processed_indices.add(pos_index)

        info['recipients'].append({
            "name": _clean_text(recipient_entity['text']),
            "position": position_text
        })
        processed_indices.add(i)

    # 3. Proses Tanggal dan Kota Surat
    # Cari tanggal yang paling mungkin sebagai tanggal surat
    possible_dates = [e for e in entities_sorted if e['entity_group'] == 'DOCDATE']
    possible_cities = [e for e in entities_sorted if e['entity_group'] == 'CITY']

    # Prioritaskan tanggal yang berdekatan dengan kota
    found_doc_date = False
    for city_entity in possible_cities:
        date_entity = _find_nearby_entity(city_entity, possible_dates, processed_indices)
        if date_entity:
            info['document_city'] = _clean_text(city_entity['text'])
            info['document_date'] = _clean_text(date_entity['text'])
            processed_indices.add(entities_sorted.index(city_entity))
            processed_indices.add(entities_sorted.index(date_entity))
            found_doc_date = True
            break  # Cukup temukan satu pasang

    # Jika tidak ada pasangan kota-tanggal, ambil tanggal pertama sebagai fallback
    if not found_doc_date and possible_dates:
        first_date = possible_dates[0]
        if entities_sorted.index(first_date) not in processed_indices:
            info['document_date'] = _clean_text(first_date['text'])
            processed_indices.add(entities_sorted.index(first_date))

    # --- Finalisasi ---
    # Kumpulkan semua entitas yang tidak diproses
    remaining_entities = [
        entity for i, entity in enumerate(entities_sorted) if i not in processed_indices
    ]

    # Hapus kunci 'text' sementara dari sisa entitas jika ada
    for entity in remaining_entities:
        if 'text' in entity:
            del entity['text']

    return info, remaining_entities
