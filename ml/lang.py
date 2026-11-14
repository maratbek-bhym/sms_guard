"""Определение языка по алфавиту (допустимая ТЗ альтернатива langdetect): ru / kk / en / other."""
import re

KK_LETTERS = set("әғқңөұүһіӘҒҚҢӨҰҮҺІ")


def detect_language(text: str) -> str:
    if not isinstance(text, str):
        return "other"
    if any(c in KK_LETTERS for c in text):
        return "kk"
    cyr = len(re.findall(r"[а-яА-ЯёЁ]", text))
    lat = len(re.findall(r"[a-zA-Z]", text))
    if cyr == 0 and lat == 0:
        return "other"
    return "ru" if cyr >= lat else "en"
