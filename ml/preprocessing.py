"""Предобработка SMS. Одна и та же normalize_sms() используется при обучении и в приложении."""
from __future__ import annotations

import re
import unicodedata

_TLDS = (r"com|org|net|ru|kz|example|test|invalid|ly|gl|co|is|cc|me|io|xyz|top|click|info|biz|"
         r"gov|edu|su|by|ua|uz|kg|app|site|online|link")
_URL_RE = re.compile(
    r"(?i)(?:\b(?:https?://|www\.)[^\s<>\"']+"
    r"|(?<![\w@.-])[\w\-]+(?:\.[\w\-]+)*\.(?:" + _TLDS + r")\b(?:[/:?#][^\s<>\"']*)?)"
)
_EMAIL_RE = re.compile(r"(?i)\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_CUR = r"(?:[$£€₸₽]|руб(?:лей|ля|\.)?|р\.|тг\.?|тенге|теңге|tenge|usd|eur|kzt|rub|dollars?|долл(?:аров|\.)?)"
_NUM = r"\d(?:[\d\s.,]*\d)?"
_MONEY_RE = re.compile(r"(?i)(?:[$£€₸₽]\s?" + _NUM + r"|" + _NUM + r"\s?" + _CUR + r"(?!\w))")
_PHONE_RE = re.compile(r"(?<![\w<])\+?\d[\d\s\-()]{7,}\d(?!\w)")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
_WS_RE = re.compile(r"\s+")
_TRAIL = ".,;:!?)»\"'"


def _url_repl(m: re.Match) -> str:
    s = m.group(0)
    tail = ""
    while s and s[-1] in _TRAIL:
        tail = s[-1] + tail
        s = s[:-1]
    return "<url>" + tail


def normalize_sms(text) -> str:
    """Чистая функция: NFKC, нижний регистр, токены <url> <email> <phone> <money> <num>.

    Сохраняются казахские буквы, ! и ? (повторы схлопываются). Пустой/нестроковый ввод -> ''.
    """
    if not isinstance(text, str) or not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = "".join(" " if unicodedata.category(c) in ("Cc", "Cf") else c for c in t)
    t = t.lower()
    t = _URL_RE.sub(_url_repl, t)
    t = _EMAIL_RE.sub("<email>", t)
    t = _MONEY_RE.sub("<money>", t)
    t = _PHONE_RE.sub("<phone>", t)
    t = _NUM_RE.sub("<num>", t)
    t = re.sub(r"!{2,}", "!", t)
    t = re.sub(r"\?{2,}", "?", t)
    return _WS_RE.sub(" ", t).strip()
