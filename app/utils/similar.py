from difflib import SequenceMatcher  # Untuk membandingkan kemiripan string


def similar(a, b, threshold=0.6):  # Fungsi untuk cek kemiripan string
    return SequenceMatcher(None, a, b).ratio(), SequenceMatcher(None, a, b).ratio() >= threshold
