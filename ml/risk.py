"""Risk Score 0–100: формула ТЗ + правила усиления; веса и пороги — в risk_config.yaml."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ml.rules import group_title

CONFIG_PATH = Path(os.environ.get("RISK_CONFIG", Path(__file__).resolve().parents[1] / "risk_config.yaml"))
_cache = {"mtime": None, "path": None, "cfg": None}

RECOMMENDATIONS = {
    "HIGH": "Не переходите по ссылке, не сообщайте коды и данные карты. Свяжитесь с банком по номеру с обратной стороны карты.",
    "MEDIUM": "Будьте осторожны: не переходите по ссылке и не вводите данные, пока не проверите отправителя другим способом.",
    "LOW": "Явных признаков мошенничества не найдено, но не вводите пароли и данные карты по ссылкам из сообщений.",
}


def load_config(path=None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    m = p.stat().st_mtime
    if _cache["path"] != str(p) or _cache["mtime"] != m:
        _cache.update(path=str(p), mtime=m, cfg=yaml.safe_load(p.read_text(encoding="utf-8")))
    return _cache["cfg"]


@dataclass
class RiskResult:
    score: int
    level: str            # LOW / MEDIUM / HIGH
    category: str         # SAFE / SUSPICIOUS / FRAUDULENT
    reasons: list = field(default_factory=list)
    recommendation: str = ""
    applied_rules: list = field(default_factory=list)


def level_for(score: float, cfg: dict):
    lv = cfg["levels"]
    if score >= lv["high_min"]:
        return "HIGH", "FRAUDULENT"
    if score >= lv["medium_min"]:
        return "MEDIUM", "SUSPICIOUS"
    return "LOW", "SAFE"


def compute_risk(p_sms, p_url_max, se_groups, url_flags=None, cfg=None, url_reasons=None,
                 code_warning=False, text_present=True) -> RiskResult:
    """p_sms / p_url_max: float или None (нет модели / нет ссылки); se_groups: список кодов групп;
    url_flags: {'has_ip': bool, 'punycode_brand': bool}; text_present=False для проверки одного URL."""
    cfg = cfg or load_config()
    w = cfg["weights"]
    url_flags = url_flags or {}
    se_groups = list(se_groups or [])
    k = len(se_groups)
    s_se = min(k / cfg["se_saturation_groups"], 1.0)
    num = den = 0.0
    if p_sms is not None:
        num += w["sms"] * p_sms; den += w["sms"]
    if p_url_max is not None:
        num += w["url"] * p_url_max; den += w["url"]
    if text_present:
        num += w["se"] * s_se; den += w["se"]
    score = 100.0 * num / den if den else 0.0
    applied, ov = [], cfg["overrides"]
    if "CODE_REQUEST" in se_groups and score < ov["code_request_min"]:
        score = ov["code_request_min"]; applied.append("CODE_REQUEST")
    c = ov["sms_url_combo"]
    if p_sms is not None and p_url_max is not None and p_sms >= c["p_sms_min"] and p_url_max >= cfg["url_t2"] and score < c["min_score"]:
        score = c["min_score"]; applied.append("SMS_URL_COMBO")
    if (url_flags.get("has_ip") or url_flags.get("punycode_brand")) and score < ov["url_ip_or_punycode_min"]:
        score = ov["url_ip_or_punycode_min"]; applied.append("URL_IP_OR_PUNYCODE")
    mit = cfg.get("mitigation", {})
    if (code_warning and "CODE_REQUEST" not in se_groups and mit.get("code_warning_penalty")
            and not (mit.get("apply_only_without_url") and p_url_max is not None)):
        score = max(score - mit["code_warning_penalty"], 0); applied.append("CODE_WARNING_MITIGATION")
    score = int(round(min(max(score, 0.0), 100.0)))
    level, category = level_for(score, cfg)
    # причины, отсортированные по вкладу
    cand = []
    if p_sms is not None and p_sms > 0.5:
        cand.append((w["sms"] * p_sms, f"Модель оценки текста считает сообщение похожим на мошенническое (P = {p_sms:.2f})"))
    if p_url_max is not None and p_url_max > 0.5:
        cand.append((w["url"] * p_url_max, f"Модель оценки ссылок считает ссылку опасной (P = {p_url_max:.2f})"))
    for g in se_groups:
        cand.append((w["se"] / max(cfg["se_saturation_groups"], 1) + (0.5 if g == "CODE_REQUEST" else 0.0), group_title(g)))
    for r in (url_reasons or []):
        cand.append((0.01, "Ссылка: " + r[0].lower() + r[1:]))
    if "CODE_REQUEST" in applied:
        cand.append((0.6, "Просьба назвать код — типичный признак мошенничества, оценка повышена"))
    if not cand:
        cand.append((0.0, "Признаков мошенничества не обнаружено"))
    cand.sort(key=lambda t: -t[0])
    reasons = []
    for _, r in cand:
        if r not in reasons:
            reasons.append(r)
    return RiskResult(score, level, category, reasons[: cfg.get("reasons_max", 6)], RECOMMENDATIONS[level], applied)
