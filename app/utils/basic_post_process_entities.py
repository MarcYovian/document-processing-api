import re
import pandas as pd

from app.utils.cek_date_year import cek_date_year


def basic_post_process_entities(raw_predictions_list):
    """Melakukan pembersihan dasar pada daftar entitas hasil NER pipeline."""
    if not raw_predictions_list:
        return []

    df = pd.DataFrame(raw_predictions_list)

    # B. Hapus entitas ORG yang terlalu pendek (misalnya, 1 karakter)
    df = df[~((df['entity_group'] == 'ORG') & (df['word'].str.len() <= 1))]

    # C. Bersihkan PEOQTY untuk hanya mengambil angka
    def clean_peoqty(text):
        if isinstance(text, str):
            match = re.search(r"^\d+", text)  # Cari angka di awal
            return match.group(0) if match else text  # Kembalikan hanya angka jika ditemukan
        return str(text) if pd.notna(text) else text

    if 'PEOQTY' in df['entity_group'].unique():
        df.loc[df['entity_group'] == 'PEOQTY', 'word'] = df.loc[df['entity_group'] == 'PEOQTY', 'word'].apply(
            clean_peoqty)

    def normalize_email(text):
        if isinstance(text, str) and "@" not in text and "gmail.com" not in text:  # Heuristik sederhana
            return f"{text}@gmail.com"  # Asumsi default, perlu disesuaikan
        return text

    if 'EMAIL' in df['entity_group'].unique():
        df.loc[df['entity_group'] == 'EMAIL', 'word'] = df.loc[df['entity_group'] == 'EMAIL', 'word'].apply(
            normalize_email)

    # D. Contoh penggabungan DOCNUM yang terpisah (heuristik sederhana)
    # Ini memerlukan iterasi dan lebih baik dilakukan pada list of dicts
    processed_entities = []
    if 'start' not in df.columns:
        print("Peringatan: DataFrame tidak memiliki kolom 'start'. Penggabungan DOCNUM mungkin tidak akurat.")
        # Kembalikan DataFrame yang sudah diproses sebagian jika tidak ada 'start'
        return df.to_dict(orient='records')

    temp_list = df.sort_values(by='start').to_dict(orient='records')
    i = 0
    while i < len(temp_list):
        current_entity = temp_list[i].copy()

        if current_entity['entity_group'] == 'DOCNUM':
            # Simpan detail asli untuk penggabungan yang aman
            current_word = str(current_entity['word'])
            current_end = current_entity.get('end', current_entity.get('start', 0))
            current_score = current_entity.get('score', 1.0)  # Default score jika tidak ada

            # 1. Coba gabungkan dengan DOCNUM berikutnya jika merupakan kelanjutan
            if i + 1 < len(temp_list):
                next_entity_candidate = temp_list[i + 1]
                if next_entity_candidate.get('entity_group') == 'DOCNUM' and \
                        next_entity_candidate.get('start') == current_end and \
                        str(next_entity_candidate.get('word', '')).strip().startswith('/'):
                    current_word += str(next_entity_candidate['word']).replace('/ ', '/')  # Bersihkan spasi setelah /
                    current_end = next_entity_candidate.get('end', current_end)
                    current_score = min(current_score, next_entity_candidate.get('score', 1.0))
                    i += 1  # Lewati entitas berikutnya karena sudah digabung

            # Update current_entity dengan hasil penggabungan DOCNUM-DOCNUM (jika ada)
            current_entity['word'] = current_word
            current_entity['end'] = current_end
            current_entity['score'] = current_score

            # 2. Coba gabungkan dengan DOCDATE/DATE berikutnya yang sesuai (bulan/tahun, atau hanya tahun)
            idx_for_date_check = i + 1
            if idx_for_date_check < len(temp_list):
                date_entity = temp_list[idx_for_date_check]
                date_entity_group = date_entity.get('entity_group')
                date_entity_word_str = str(date_entity.get('word', '')).strip()

                is_appendable_date_part = False
                cleaned_date_part_for_docnum = ""

                if date_entity_group in ['DOCDATE', 'DATE']:
                    # Pola: "vii / 2024", "Mei / 2024", "5 / 2024" (dengan spasi fleksibel)
                    match_month_year = re.fullmatch(r"([a-zA-Z\dIVXLCDMivxlcdm]+)\s*/\s*(\d{4})", date_entity_word_str,
                                                    re.IGNORECASE)

                    match_slash_year = re.fullmatch(r"/\s*(\d{4})", date_entity_word_str)

                    if match_month_year:
                        # Gabungkan bulan dan tahun dengan satu slash
                        cleaned_date_part_for_docnum = f"{match_month_year.group(1)}/{match_month_year.group(2)}"
                        is_appendable_date_part = True
                    elif match_slash_year:
                        # Ambil hanya bagian tahunnya saja
                        cleaned_date_part_for_docnum = match_slash_year.group(1)  # group(1) adalah (\d{4})
                        is_appendable_date_part = True
                    # Pola: Hanya tahun (misalnya "2024")
                    elif cek_date_year(date_entity_word_str):  # cek_date_year harus hanya memvalidasi format tahun YYYY
                        cleaned_date_part_for_docnum = date_entity_word_str
                        is_appendable_date_part = True

                if is_appendable_date_part:
                    # Heuristik kedekatan: entitas tanggal harus muncul segera setelah DOCNUM
                    # atau dengan sedikit spasi (misalnya, tidak lebih dari 5 karakter)
                    max_gap_for_date_in_docnum = 5
                    if date_entity.get('start', float('inf')) - current_entity.get('end', current_entity.get('start',
                                                                                                             0)) <= max_gap_for_date_in_docnum:

                        # Bersihkan bagian akhir DOCNUM saat ini
                        docnum_to_append = str(current_entity['word']).strip()
                        if docnum_to_append.endswith('/'):
                            docnum_to_append = docnum_to_append[:-1].strip()

                        current_entity['word'] = docnum_to_append + "/" + cleaned_date_part_for_docnum
                        current_entity['end'] = date_entity.get('end', current_entity.get('end'))
                        current_entity['score'] = min(current_entity.get('score', 1.0), date_entity.get('score', 1.0))
                        i += 1  # Lewati entitas tanggal karena sudah digabung

        processed_entities.append(current_entity)
        i += 1

    return processed_entities
