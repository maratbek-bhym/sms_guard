"""Признаки URL. URL анализируется только как строка: никаких сетевых запросов и DNS."""
from __future__ import annotations

import ipaddress
import math
import re
from collections import Counter, namedtuple
from urllib.parse import parse_qsl, urlsplit

MAX_URL_LEN = 2048
ValidationResult = namedtuple("ValidationResult", "ok error normalized")

SHORTENERS = frozenset({
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "is.gd", "cutt.ly", "ow.ly", "clck.ru", "rebrand.ly",
    "buff.ly", "shorturl.at", "tiny.cc", "v.gd", "bl.ink", "rb.gy", "s.id", "lnkd.in", "vk.cc",
    # искусственные сокращатели на зарезервированных доменах (для синтетических данных)
    "lnk.example", "shrt.test", "go-link.test", "sho.invalid", "tiny-link.test", "u.example",
    "short.invalid", "jmp.test",
})
SUSPICIOUS_WORDS = (
    "login", "signin", "verify", "secure", "account", "update", "bank", "confirm", "password",
    "bonus", "free", "prize", "kaspi", "halyk", "wallet", "billing", "suspend", "unlock", "claim",
    "gift", "refund", "support", "auth", "credential", "payment",
)
SUSPICIOUS_TLDS = frozenset({"xyz", "top", "click", "zip", "work", "loan", "gq", "tk", "ml", "cf",
                             "ga", "icu", "buzz", "country", "kim", "mov"})
BRANDS = ("kaspi", "halyk", "sberbank", "tinkoff", "alfabank", "forte", "jusan", "paypal", "google",
          "apple", "microsoft", "amazon", "facebook", "instagram", "netflix", "dhl", "fedex",
          "kazpost", "egov", "telegram", "whatsapp", "binance", "chase", "wellsfargo", "barclays", "hsbc")
MULTI_SUFFIXES = frozenset({"co.uk", "com.kz", "org.kz", "com.au", "co.jp", "com.ru", "com.tr", "co.in"})

FEATURE_NAMES = (
    "url_length", "host_length", "path_length", "num_dots", "num_subdomains", "num_hyphens_host",
    "num_digits_url", "digit_ratio_host", "num_special_chars", "has_ip", "is_https", "nonstandard_port",
    "has_at", "double_slash_in_path", "is_shortener", "num_suspicious_words", "has_punycode",
    "mixed_script", "brand_lookalike", "host_entropy", "suspicious_tld", "num_query_params",
    "path_depth", "brand_in_host_mismatch", "query_length", "longest_label_len", "has_random_token",
)

_SCHEME_NO_SLASH = re.compile(r"^([a-z][a-z0-9+.\-]*):(?!//)(.*)$", re.I | re.S)
_TOKEN_RE = re.compile(r"[A-Za-z0-9]{12,}")


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def validate_url(url) -> ValidationResult:
    """Проверка формата (ФТ-3.1). URL без схемы дополняется http:// только для разбора."""
    if not isinstance(url, str):
        return ValidationResult(False, "Ссылка должна быть строкой", "")
    s = url.strip()
    if not s:
        return ValidationResult(False, "Ссылка не может быть пустой", "")
    if len(s) > MAX_URL_LEN:
        return ValidationResult(False, f"Ссылка длиннее {MAX_URL_LEN} символов", "")
    if any(ord(c) < 32 or c.isspace() for c in s):
        return ValidationResult(False, "Ссылка не должна содержать пробелы и управляющие символы", "")
    if "://" in s:
        scheme = s.split("://", 1)[0].lower()
        if scheme not in ("http", "https"):
            return ValidationResult(False, "Допустимы только схемы http и https", "")
        norm = s
    else:
        m = _SCHEME_NO_SLASH.match(s)
        if m and not re.match(r"^\d+(?:[/?#]|$)", m.group(2)):
            return ValidationResult(False, "Допустимы только схемы http и https", "")
        norm = "http://" + s
    try:
        parts = urlsplit(norm)
        host = parts.hostname
        _ = parts.port
    except ValueError:
        return ValidationResult(False, "Некорректный формат ссылки", "")
    if not host:
        return ValidationResult(False, "В ссылке не найден домен", "")
    if not _is_ip(host) and "." not in host:
        return ValidationResult(False, "В ссылке не найден домен (нет точки в имени узла)", "")
    if not _is_ip(host) and not re.fullmatch(r"[\w.\-]+", host):
        return ValidationResult(False, "Домен содержит недопустимые символы", "")
    return ValidationResult(True, "", norm)


def registrable_domain(host: str) -> str:
    """Упрощённый регистрируемый домен без внешних списков публичных суффиксов."""
    if not host or _is_ip(host):
        return host or ""
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    if ".".join(labels[-2:]) in MULTI_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def _scripts_mixed(host: str) -> bool:
    try:
        host = host.encode("ascii").decode("idna")
    except (UnicodeError, ValueError):
        pass
    for label in host.split("."):
        cyr = any("\u0400" <= c <= "\u04ff" for c in label)
        lat = any("a" <= c.lower() <= "z" for c in label)
        if cyr and lat:
            return True
    return False


def _zero() -> dict:
    return {k: 0.0 for k in FEATURE_NAMES}


def extract_url_features(url) -> dict:
    """Словарь с фиксированным набором и порядком признаков. Не вызывает исключений."""
    feats = _zero()
    try:
        v = validate_url(url)
        if not v.ok:
            return feats
        raw = v.normalized
        parts = urlsplit(raw)
        host = (parts.hostname or "").lower()
        path, query = parts.path or "", parts.query or ""
        ip = _is_ip(host)
        reg = registrable_domain(host)
        sld = reg.split(".")[0] if not ip else ""
        labels = [] if ip else host.split(".")
        tld = labels[-1] if labels else ""
        n_sub = 0 if ip else max(len(host.split(".")) - len(reg.split(".")), 0)
        low = raw.lower()
        try:
            port = parts.port
        except ValueError:
            port = None
        feats.update({
            "url_length": len(raw), "host_length": len(host), "path_length": len(path),
            "num_dots": raw.count("."), "num_subdomains": n_sub, "num_hyphens_host": host.count("-"),
            "num_digits_url": sum(c.isdigit() for c in raw),
            "digit_ratio_host": (sum(c.isdigit() for c in host) / len(host)) if host else 0.0,
            "num_special_chars": sum(raw.count(c) for c in "@~%=&_?"),
            "has_ip": int(ip), "is_https": int(parts.scheme == "https"),
            "nonstandard_port": int(port is not None and port not in (80, 443)),
            "has_at": int("@" in raw), "double_slash_in_path": int("//" in path),
            "is_shortener": int(host in SHORTENERS or reg in SHORTENERS),
            "num_suspicious_words": sum(low.count(w) for w in SUSPICIOUS_WORDS),
            "has_punycode": int(any(l.startswith("xn--") for l in labels)),
            "mixed_script": int(_scripts_mixed(host)),
            "brand_lookalike": int((not ip) and len(sld) >= 4 and sld not in BRANDS and
                                   any(levenshtein(sld, b) <= 2 for b in BRANDS)),
            "host_entropy": _entropy(host.replace(".", "")),
            "suspicious_tld": int(tld in SUSPICIOUS_TLDS),
            "num_query_params": len(parse_qsl(query, keep_blank_values=True)),
            "path_depth": len([p for p in path.split("/") if p]),
            "brand_in_host_mismatch": int((not ip) and any(b in host for b in BRANDS if b != sld)),
            "query_length": len(query),
            "longest_label_len": max((len(l) for l in labels), default=0),
            "has_random_token": int(bool(_TOKEN_RE.search(path + "?" + query))),
        })
        return {k: float(feats[k]) for k in FEATURE_NAMES}
    except Exception:  # noqa: BLE001 — контракт: некорректный ввод не вызывает исключений
        return _zero()


def explain_url(features: dict) -> list:
    """Человекочитаемые причины (на русском) по словарю признаков."""
    r = []
    f = features
    if f.get("has_ip"):
        r.append("Используется IP-адрес вместо доменного имени")
    if f.get("has_punycode"):
        r.append("Домен содержит Punycode (xn--) — возможна маскировка под другой адрес")
    if f.get("mixed_script"):
        r.append("В домене смешаны кириллица и латиница")
    if f.get("brand_lookalike"):
        r.append("Домен похож на название известного бренда, но не совпадает с ним")
    elif f.get("brand_in_host_mismatch"):
        r.append("Название известного бренда используется не в основном домене сайта")
    if f.get("is_shortener"):
        r.append("Используется сервис сокращения ссылок — конечный адрес скрыт")
    if f.get("has_at"):
        r.append("В адресе есть символ @ — часть адреса до него может вводить в заблуждение")
    if f.get("nonstandard_port"):
        r.append("Указан нестандартный порт")
    if f.get("double_slash_in_path"):
        r.append("В пути есть двойной слэш //")
    if f.get("num_suspicious_words", 0) >= 1:
        r.append(f"Найдены подозрительные слова в адресе: {int(f['num_suspicious_words'])}")
    if f.get("num_subdomains", 0) >= 3:
        r.append("Слишком много поддоменов")
    if f.get("suspicious_tld"):
        r.append("Подозрительная доменная зона")
    if not f.get("is_https") and f.get("url_length"):
        r.append("Соединение без HTTPS")
    if f.get("url_length", 0) > 100:
        r.append("Очень длинный адрес")
    if f.get("has_random_token"):
        r.append("В адресе есть длинная случайная последовательность символов")
    return r
