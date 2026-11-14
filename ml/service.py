"""Сервис совместного анализа: analyze_sms(text) и analyze_url(url) -> AnalysisResult."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from ml.lang import detect_language
from ml.predictor import ModelUnavailable, Predictor
from ml.risk import compute_risk, load_config
from ml.rules import RULES, find_groups, has_code_warning
from ml.url_features import explain_url, extract_url_features, validate_url

MAX_URLS = 3
_TLD = r"(?:example|test|invalid|com|org|net|ru|kz|ly|co|io|xyz|top|click|me|gl|is|cc|info|biz|su|by|ua|uz|kg|app|site|online|link|рф|қаз)"
URL_RE = re.compile(
    r"(?i)(?:\bhttps?://[^\s<>\"']+"
    r"|\bwww\.[^\s<>\"']+"
    r"|(?<![\w@.\-/])\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?/[^\s<>\"']*"
    r"|(?<![\w@.\-/])[\w\-]+(?:\.[\w\-]+)*\." + _TLD + r"(?![\w\-])(?::\d+)?(?:/[^\s<>\"']*)?)"
)
_TRAIL = ".,;:!?)»\"'"
DISCLAIMER_DEFAULT = "Оценка носит вероятностный характер и не гарантирует безопасность"
SYNTH_WARNING = "Модели обучены только на синтетических данных: реальное качество не подтверждено."
LANG_WARNINGS = {
    "ru": "Для русского языка качество ML-оценки текста не подтверждено на реальных данных; опирайтесь также на признаки и правила.",
    "kk": "Для казахского языка качество ML-оценки текста не подтверждено; работают словарь правил и анализ ссылок, ML-оценка ненадёжна.",
    "other": "Язык сообщения не представлен в обучающих данных: оценка менее надёжна.",
    "en": "Английский: модель обучена на синтетических шаблонах, а не на реальных SMS.",
}


@dataclass
class AnalysisResult:
    type: str
    language: str
    category: str
    risk_level: str
    risk_score: int
    p_sms: float | None
    urls: list = field(default_factory=list)
    features: list = field(default_factory=list)
    explanation: list = field(default_factory=list)
    recommendation: str = ""
    disclaimer: str = DISCLAIMER_DEFAULT
    model_versions: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    p_url_max: float | None = None
    applied_rules: list = field(default_factory=list)
    id: int | None = None
    created_at: str = ""

    def to_dict(self):
        return asdict(self)


def extract_urls(text: str) -> list:
    """До 3 уникальных URL (со схемой, www., IP, домены без схемы, в т.ч. сокращатели)."""
    out = []
    for m in URL_RE.finditer(text or ""):
        u = m.group(0).rstrip(_TRAIL)
        if u and u not in out:
            out.append(u)
        if len(out) == MAX_URLS:
            break
    return out


def _url_item(pred: Predictor, url: str) -> dict:
    v = validate_url(url)
    feats = extract_url_features(url)
    p = pred.p_url(url)
    from urllib.parse import urlsplit
    host = (urlsplit(v.normalized).hostname or "") if v.ok else ""
    return {"url": url, "domain": host, "p_url": round(p, 4), "category": pred.url_category(p), "features": feats,
            "reasons": explain_url(feats), "valid": v.ok, "error": v.error}


def _flags(items):
    ip = any(i["features"].get("has_ip") for i in items)
    pb = any(i["features"].get("has_punycode") and (i["features"].get("brand_lookalike") or i["features"].get("brand_in_host_mismatch") or i["features"].get("mixed_script")) for i in items)
    return {"has_ip": ip, "punycode_brand": pb}


def analyze_sms(text: str, predictor: Predictor | None = None, cfg=None) -> AnalysisResult:
    pred = predictor or Predictor.get()
    cfg = cfg or load_config()
    if pred.sms is None or pred.url is None:
        raise ModelUnavailable("Анализ недоступен: модель не загружена")
    lang = detect_language(text)
    groups = find_groups(text)
    p_sms = pred.p_sms(text)
    items = [_url_item(pred, u) for u in extract_urls(text)]
    valid = [i for i in items if i["valid"]]
    p_url_max = max((i["p_url"] for i in valid), default=None)
    url_reasons = [r for i in valid for r in i["reasons"][:2]][:3]
    rr = compute_risk(p_sms, p_url_max, list(groups), _flags(valid), cfg=cfg, url_reasons=url_reasons,
                      code_warning=has_code_warning(text))
    warns = [SYNTH_WARNING, LANG_WARNINGS[lang]]
    return AnalysisResult("SMS", lang, rr.category, rr.level, rr.score, round(p_sms, 4),
                          [{k: v for k, v in i.items() if k in ("url", "domain", "p_url", "category", "reasons")} for i in items],
                          list(groups), rr.reasons, rr.recommendation, cfg.get("disclaimer", DISCLAIMER_DEFAULT), pred.versions, warns,
                          p_url_max, rr.applied_rules, None, datetime.now(timezone.utc).isoformat())


def analyze_url(url: str, predictor: Predictor | None = None, cfg=None) -> AnalysisResult:
    pred = predictor or Predictor.get()
    cfg = cfg or load_config()
    v = validate_url(url)
    if not v.ok:
        raise ValueError(v.error)
    if pred.url is None:
        raise ModelUnavailable("Анализ ссылок недоступен: модель не загружена")
    item = _url_item(pred, url)
    rr = compute_risk(None, item["p_url"], [], _flags([item]), cfg=cfg, url_reasons=[(r) for r in item["reasons"]], text_present=False)
    return AnalysisResult("URL", "other", rr.category, rr.level, rr.score, None,
                          [{k: v for k, v in item.items() if k in ("url", "domain", "p_url", "category", "reasons", "features")}],
                          [], rr.reasons, rr.recommendation, cfg.get("disclaimer", DISCLAIMER_DEFAULT), {"sms": None, "url": pred.versions["url"]},
                          [SYNTH_WARNING], item["p_url"], rr.applied_rules, None, datetime.now(timezone.utc).isoformat())
