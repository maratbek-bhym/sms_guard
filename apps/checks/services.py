"""Мост между Django и ML-ядром. Классификации здесь нет: только вызов ml.service и сохранение результата.

Логи: содержимое SMS и URL сюда не попадает (логируются только id, тип и итог).
Сеть: ml.service не открывает URL и не делает DNS-запросов; здесь тоже нет сетевых вызовов.
"""
import logging
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from ml.predictor import ModelUnavailable, Predictor
from ml.service import analyze_sms, analyze_url

from .models import Check

log = logging.getLogger("sms_guard.checks")

__all__ = ["ModelUnavailable", "check_sms", "check_url", "model_health", "dashboard_stats"]


def model_health() -> dict:
    return Predictor.get().health()   # синглтон: модели грузятся один раз за процесс


def _store(user, res, *, text="", save_text=False, strip_urls=False) -> Check:
    urls = res.urls
    if strip_urls:   # SMS без согласия: полные URL (часть текста SMS) не сохраняем, оставляем домен и оценку
        urls = [{k: v for k, v in u.items() if k != "url"} for u in urls]
    c = Check.objects.create(
        user=user, kind=res.type, language=res.language, category=res.category, risk_level=res.risk_level,
        risk_score=res.risk_score, p_sms=res.p_sms, p_url_max=res.p_url_max,
        text_saved=bool(save_text), sms_text=text if save_text else "", text_length=len(text),
        urls=urls, se_groups=res.features, reasons=res.explanation, warnings=res.warnings,
        applied_rules=res.applied_rules, model_versions=res.model_versions,
        recommendation=res.recommendation, disclaimer=res.disclaimer,
    )
    c.live_urls = res.urls   # не сохраняется в БД: нужен только для немедленного показа результата
    log.info("check saved id=%s kind=%s category=%s score=%s", c.pk, c.kind, c.category, c.risk_score)
    return c


def check_sms(user, text: str, save_text: bool = False) -> Check:
    """Raises ModelUnavailable."""
    res = analyze_sms(text)
    return _store(user, res, text=text, save_text=save_text, strip_urls=not save_text)


def check_url(user, url: str) -> Check:
    """Raises ModelUnavailable, ValueError (некорректный URL)."""
    res = analyze_url(url)
    return _store(user, res, text=url, save_text=False)


def dashboard_stats(user, days: int = 14) -> dict:
    qs = Check.objects.filter(user=user)
    agg = qs.aggregate(
        total=Count("id"), sms=Count("id", filter=Q(kind="SMS")), url=Count("id", filter=Q(kind="URL")),
        safe=Count("id", filter=Q(category="SAFE")), suspicious=Count("id", filter=Q(category="SUSPICIOUS")),
        fraud=Count("id", filter=Q(category="FRAUDULENT")), avg=Avg("risk_score"),
    )
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    per_day = {r["d"]: r["n"] for r in qs.filter(created_at__date__gte=start).annotate(d=TruncDate("created_at"))
               .values("d").annotate(n=Count("id"))}
    series = [{"date": (start + timedelta(days=i)).isoformat(), "count": per_day.get(start + timedelta(days=i), 0)}
              for i in range(days)]
    return {
        "total": agg["total"], "by_kind": {"SMS": agg["sms"], "URL": agg["url"]},
        "by_category": {"SAFE": agg["safe"], "SUSPICIOUS": agg["suspicious"], "FRAUDULENT": agg["fraud"]},
        "avg_risk": round(agg["avg"], 1) if agg["avg"] is not None else None,
        "per_day": series,
    }


def filter_checks(qs, f: dict):
    """Фильтры истории (f — cleaned_data HistoryFilterForm). Только ORM: параметры не попадают в SQL строкой."""
    if f.get("kind"):
        qs = qs.filter(kind=f["kind"])
    if f.get("category"):
        qs = qs.filter(category=f["category"])
    if f.get("date_from"):
        qs = qs.filter(created_at__date__gte=f["date_from"])
    if f.get("date_to"):
        qs = qs.filter(created_at__date__lte=f["date_to"])
    if f.get("min_score") is not None:
        qs = qs.filter(risk_score__gte=f["min_score"])
    return qs
