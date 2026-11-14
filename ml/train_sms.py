"""Сравнение SMS-моделей на синтетическом наборе (реальный UCI-набор недоступен офлайн).
Запуск: python -m ml.train_sms"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, fbeta_score, precision_recall_curve,
                             precision_score, recall_score, f1_score, roc_auc_score, accuracy_score)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, MaxAbsScaler
from sklearn.svm import LinearSVC
from sklearn.metrics import make_scorer

from ml.preprocessing import normalize_sms

ROOT = Path(__file__).resolve().parents[1]
ART, REP = ROOT / "ml" / "artifacts", ROOT / "data" / "reports"
F2 = make_scorer(fbeta_score, beta=2)


def manual_features(texts):
    """6 ручных признаков по исходному тексту: длина, доля заглавных, число !, наличие url/money, доля цифр."""
    out = []
    for t in texts:
        t = t if isinstance(t, str) else ""
        n = max(len(t), 1)
        c = normalize_sms(t)
        out.append([min(len(t), 1000) / 1000, sum(ch.isupper() for ch in t) / n, min(t.count("!"), 5) / 5,
                    float("<url>" in c), float("<money>" in c), sum(ch.isdigit() for ch in t) / n])
    return np.array(out)


def select_text(d):
    """Выбор текстового столбца из DataFrame (функция уровня модуля — нужна для joblib)."""
    return d["text"].values if hasattr(d, "columns") else np.asarray(d, dtype=object)


def build(clf, use_char=True, use_manual=True):
    from sklearn.pipeline import FeatureUnion

    def sel():
        return FunctionTransformer(select_text, validate=False)

    word = TfidfVectorizer(preprocessor=normalize_sms, ngram_range=(1, 2), min_df=2, max_df=0.95, sublinear_tf=True)
    union = [("word", Pipeline([("s", sel()), ("v", word)]))]
    if use_char:
        char = TfidfVectorizer(preprocessor=normalize_sms, analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)
        union.append(("char", Pipeline([("s", sel()), ("v", char)])))
    if use_manual:
        union.append(("manual", Pipeline([("s", sel()), ("m", FunctionTransformer(manual_features, validate=False)), ("sc", MaxAbsScaler())])))
    return Pipeline([("feats", FeatureUnion(union)), ("clf", clf)])


def metrics(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"accuracy": accuracy_score(y, pred), "precision": precision_score(y, pred, zero_division=0),
            "recall": recall_score(y, pred), "f1": f1_score(y, pred), "f2": fbeta_score(y, pred, beta=2),
            "roc_auc": roc_auc_score(y, p) if len(set(y)) > 1 else None,
            "pr_auc": average_precision_score(y, p) if len(set(y)) > 1 else None,
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp), "threshold": float(thr)}


def pick_threshold(y, p, min_prec=0.85):
    pr, rc, th = precision_recall_curve(y, p)
    ok = [(r, t) for pp, r, t in zip(pr[:-1], rc[:-1], th) if pp >= min_prec]
    return float(max(ok)[1]) if ok else 0.5   # максимальный Recall при Precision >= min_prec


def main():
    d = pd.read_csv(ROOT / "data/processed/sms/sms_all.csv")
    tr, va, te = (d[d.split == s].reset_index(drop=True) for s in ("train", "val", "test"))
    ytr, yva, yte = tr.label.astype(int).values, va.label.astype(int).values, te.label.astype(int).values
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    cands = {
        "MultinomialNB": (MultinomialNB(), {"clf__alpha": [0.01, 0.1, 0.5, 1.0]}),
        "LogisticRegression": (LogisticRegression(class_weight="balanced", max_iter=1000), {"clf__C": [0.3, 1, 3, 10, 30]}),
        "LinearSVC+Calibrated": (CalibratedClassifierCV(LinearSVC(class_weight="balanced"), cv=3), {"clf__estimator__C": [0.1, 0.3, 1, 3]}),
    }
    table, fitted = [], {}
    for name, (clf, grid) in cands.items():
        for variant, kw in (("word+char+manual", {}), ("word_only", {"use_char": False, "use_manual": False})):
            t0 = time.time()
            gs = GridSearchCV(build(clf, **kw), grid, scoring=F2, cv=cv, n_jobs=-1)
            gs.fit(tr[["text"]], ytr, groups=tr.family.values)
            fit_s = time.time() - t0
            t1 = time.time()
            p = gs.predict_proba(va[["text"]])[:, 1]
            ms = (time.time() - t1) / len(va) * 1000
            m = metrics(yva, p)
            m.update({"model": name, "features": variant, "best_params": gs.best_params_, "cv_f2": gs.best_score_,
                      "fit_seconds": round(fit_s, 1), "predict_ms_per_sms": round(ms, 3)})
            table.append(m)
            fitted[(name, variant)] = (gs, p)
            print(f"{name:22s} {variant:18s} val F2={m['f2']:.3f} P={m['precision']:.3f} R={m['recall']:.3f} AUC={m['roc_auc']:.3f} cvF2={gs.best_score_:.3f}")
    # выбор: максимум F2 на валидации при Precision >= 0.85
    ok = [m for m in table if m["precision"] >= 0.85] or table
    best = max(ok, key=lambda m: m["f2"])
    gs, p_val = fitted[(best["model"], best["features"])]
    thr = pick_threshold(yva, p_val)
    print("ВЫБРАНО:", best["model"], best["features"], "порог", round(thr, 4))
    # единственная оценка на test
    p_te = gs.predict_proba(te[["text"]])[:, 1]
    test_m = metrics(yte, p_te, thr)
    per_lang = {l: metrics(yte[te.lang.values == l], p_te[te.lang.values == l], thr) for l in ("ru", "kk", "en")}
    per_cat = te.assign(pred=(p_te >= thr).astype(int), y=yte).groupby(["class3", "category"]).apply(
        lambda g: {"n": len(g), "error_rate": round(float((g.pred != g.y).mean()), 3)}, include_groups=False)
    errs = te.assign(p=p_te, y=yte)
    errs = errs[(p_te >= thr).astype(int) != yte]
    fn_ex = errs[errs.y == 1].head(8)[["lang", "category", "p", "text"]].to_dict("records")
    fp_ex = errs[errs.y == 0].head(8)[["lang", "category", "p", "text"]].to_dict("records")
    # suspicious (отдельный класс): распределение вероятностей, не метрики
    sus = d[d.split == "eval_only"]
    p_sus = gs.predict_proba(sus[["text"]])[:, 1]
    sus_summary = {"n": len(sus), "mean_p": float(p_sus.mean()), "share_ge_thr": float((p_sus >= thr).mean()),
                   "by_lang_share_ge_thr": {l: float((p_sus[sus.lang.values == l] >= thr).mean()) for l in ("ru", "kk", "en")}}
    # итоговая модель: переобучение на train+val с найденными параметрами
    final = build(cands[best["model"]][0].__class__(**{k: v for k, v in cands[best["model"]][0].get_params().items()}),
                  **({} if best["features"] == "word+char+manual" else {"use_char": False, "use_manual": False}))
    final.set_params(**best["best_params"])
    trva = pd.concat([tr, va], ignore_index=True)
    final.fit(trva[["text"]], trva.label.astype(int).values)
    joblib.dump(final, ART / "sms_model.joblib")
    p_chk = joblib.load(ART / "sms_model.joblib").predict_proba(te[["text"]])[:, 1]
    meta = {"version": "1.0.0-synthetic", "algorithm": best["model"], "features": best["features"], "params": best["best_params"],
            "threshold": thr, "trained_at": datetime.now(timezone.utc).isoformat(), "train_data": "synthetic only (ru/kk/en, template-grouped split)",
            "real_data_used": False,
            "note": "Метрики получены на синтетических данных тех же генераторов; они НЕ оценивают качество на реальных SMS.",
            "validation_selection_metrics": best, "test_metrics_selected_model_trained_on_train": test_m, "test_per_language": per_lang,
            "test_per_category": {f"{k[0]}/{k[1]}": v for k, v in per_cat.items()},
            "suspicious_eval": sus_summary,
            "refit_on_train_plus_val": True, "test_proba_after_refit_mean": float(p_chk.mean())}
    json.dump(meta, open(ART / "sms_model_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump({"comparison": table, "fn_examples": fn_ex, "fp_examples": fp_ex}, open(REP / "sms_model_comparison.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("TEST (train-only fit):", {k: round(v, 3) if isinstance(v, float) else v for k, v in test_m.items()})
    for l, m in per_lang.items():
        print(l, {k: round(v, 3) if isinstance(v, float) else v for k, v in m.items() if k in ("precision", "recall", "f1", "roc_auc", "fp", "fn")})
    print("suspicious:", sus_summary)
    print("per-category worst:", sorted(((v["error_rate"], k) for k, v in meta["test_per_category"].items()), reverse=True)[:6])
    print("FN ex:", [(e["lang"], e["category"], round(e["p"], 2), e["text"][:70]) for e in fn_ex[:5]])
    print("FP ex:", [(e["lang"], e["category"], round(e["p"], 2), e["text"][:70]) for e in fp_ex[:5]])


if __name__ == "__main__":
    main()
