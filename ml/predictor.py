"""Единая точка загрузки моделей (синглтон, загрузка один раз за процесс) и предсказаний."""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

import joblib
import pandas as pd

import ml.train_sms  # noqa: F401 — нужен для распаковки pipeline (функции select_text, manual_features)
from ml.url_features import FEATURE_NAMES, extract_url_features

log = logging.getLogger("sms_guard.predictor")
ART = Path(os.environ.get("MODEL_DIR", Path(__file__).resolve().parents[1] / "ml" / "artifacts"))


class ModelUnavailable(RuntimeError):
    """Модель не загружена (отсутствует файл или он повреждён) — API должен ответить 503."""


class Predictor:
    _inst = None
    _lock = threading.Lock()

    def __init__(self, art_dir=None):
        self.art = Path(art_dir) if art_dir else ART
        self.sms = self.url = None
        self.sms_meta, self.url_meta = {}, {}
        self.errors = {}
        self._load()

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._inst is None:
                cls._inst = cls()
            return cls._inst

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._inst = None

    def _load(self):
        for kind in ("sms", "url"):
            try:
                obj = joblib.load(self.art / f"{kind}_model.joblib")
                meta = json.loads((self.art / f"{kind}_model_meta.json").read_text(encoding="utf-8"))
                if kind == "sms":
                    self.sms, self.sms_meta = obj, meta
                else:
                    self.url, self.url_meta = obj["model"], meta
                    self._url_cols = obj["features"]
                log.info("Модель %s загружена (версия %s)", kind, meta.get("version"))
            except Exception as e:  # noqa: BLE001
                self.errors[kind] = f"{type(e).__name__}: {e}"
                log.error("Модель %s недоступна: %s — анализ %s отключён", kind, self.errors[kind], kind)

    @property
    def versions(self):
        return {"sms": self.sms_meta.get("version"), "url": self.url_meta.get("version")}

    def health(self):
        return {"status": "ok" if self.sms and self.url else "degraded", "sms_model": bool(self.sms), "url_model": bool(self.url),
                "versions": self.versions, "errors": self.errors}

    def p_sms(self, text: str) -> float:
        if self.sms is None:
            raise ModelUnavailable("Модель анализа текста недоступна")
        return float(self.sms.predict_proba(pd.DataFrame({"text": [text]}))[0, 1])

    def p_url(self, url: str) -> float:
        if self.url is None:
            raise ModelUnavailable("Модель анализа ссылок недоступна")
        feats = extract_url_features(url)
        return float(self.url.predict_proba(pd.DataFrame([feats])[list(self._url_cols)])[0, 1])

    @property
    def sms_threshold(self):
        return self.sms_meta.get("threshold", 0.5)

    @property
    def url_thresholds(self):
        return self.url_meta.get("t1", 0.2), self.url_meta.get("t2", 0.5)

    def url_category(self, p: float) -> str:
        t1, t2 = self.url_thresholds
        return "SAFE" if p < t1 else ("SUSPICIOUS" if p < t2 else "DANGEROUS")
