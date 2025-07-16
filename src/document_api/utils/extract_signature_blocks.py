import re
from typing import List, Dict, Any, Tuple


def _clean_text(text: str) -> str:
    """Membersihkan teks dari spasi berlebih dan karakter tidak penting."""
    return re.sub(r'\s+', ' ', text).strip()


def _is_adjacent(entity1: Dict[str, Any], entity2: Dict[str, Any], max_gap: int = 15) -> bool:
    """Memeriksa apakah dua entitas berdekatan."""
    return (entity2['start'] - entity1['end']) < max_gap


def extract_signature_blocks(
        entities: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
    """
    Mengekstrak blok penanda tangan dengan logika pencocokan grup yang cerdas
    dan mengembalikan output berstandar API (snake_case).
    """
    if not entities:
        return [], []

    # Standarisasi kunci input
    for entity in entities:
        entity['text'] = entity.get('entity_text', '') or entity.get('word')

    entities_sorted = sorted(entities, key=lambda x: x.get('start', 0))

    signature_blocks = []
    processed_indices = set()
    i = 0
    while i < len(entities_sorted):
        if i in processed_indices:
            i += 1
            continue

        # Langkah 1: Cari grup jabatan (POSITION) yang berurutan
        pos_group = []
        if entities_sorted[i]['entity_group'] == 'POSITION':
            pos_group.append(entities_sorted[i])
            j = i + 1
            while j < len(entities_sorted) and entities_sorted[j]['entity_group'] == 'POSITION':
                if _is_adjacent(entities_sorted[j - 1], entities_sorted[j]):
                    pos_group.append(entities_sorted[j])
                    j += 1
                else:
                    break

        if not pos_group:
            i += 1
            continue

        # Langkah 2: Cari grup nama (PER) berikutnya yang berurutan
        per_group_start_index = -1
        # Lewati entitas non-PER setelah grup jabatan
        k = j
        while k < len(entities_sorted) and entities_sorted[k]['entity_group'] != 'PER':
            k += 1

        per_group = []
        if k < len(entities_sorted) and entities_sorted[k]['entity_group'] == 'PER':
            # Pastikan jarak antara jabatan terakhir dan nama pertama tidak terlalu jauh
            if (entities_sorted[k]['start'] - pos_group[-1]['end']) < 75:
                per_group.append(entities_sorted[k])
                per_group_start_index = k
                l = k + 1
                while l < len(entities_sorted) and entities_sorted[l]['entity_group'] == 'PER':
                    if _is_adjacent(entities_sorted[l - 1], entities_sorted[l]):
                        per_group.append(entities_sorted[l])
                        l += 1
                    else:
                        break

        # Langkah 3: Terapkan logika pencocokan
        if pos_group and per_group:
            # Heuristik: Jika jumlahnya sama, pasangkan satu per satu
            if len(pos_group) == len(per_group):
                for idx in range(len(pos_group)):
                    signature_blocks.append({
                        "position": _clean_text(pos_group[idx]['text']),
                        "name": _clean_text(per_group[idx]['text'])
                    })
            # Fallback: Jika tidak sama, gabungkan semua
            else:
                full_position = " ".join([_clean_text(p['text']) for p in pos_group])
                full_name = " ".join([_clean_text(p['text']) for p in per_group])
                signature_blocks.append({"position": full_position, "name": full_name})

            # Tandai semua entitas yang digunakan sebagai terpakai
            for entity in pos_group + per_group:
                processed_indices.add(entities_sorted.index(entity))

            i = per_group_start_index + len(per_group)
        else:
            i = j  # Lanjut dari akhir grup jabatan jika tidak ada nama yang cocok

    # Kumpulkan sisa entitas
    remaining_entities = [
        entity for idx, entity in enumerate(entities_sorted) if idx not in processed_indices
    ]

    # Hapus kunci 'text' sementara dari sisa entitas
    for entity in remaining_entities:
        if 'text' in entity:
            del entity['text']

    return signature_blocks, remaining_entities
