import re


def cek_date_year(text_year, minimum_year=1990, maximum_year=2099):
    """
    Memeriksa apakah teks adalah representasi tahun 4 digit yang valid
    dalam rentang tertentu.
    """
    if isinstance(text_year, str) and re.fullmatch(r"\d{4}", text_year.strip()):
        try:
            year = int(text_year.strip())
            return minimum_year <= year <= maximum_year
        except ValueError:
            return False
    return False
