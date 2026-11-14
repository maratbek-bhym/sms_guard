"""Обучение URL-модели на синтетическом наборе: python -m ml.train_url"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score, fbeta_score,
                             make_scorer, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.url_features import FEATURE_NAMES, extract_url_features

ROOT = Path(__file__).resolve().parents[1]
ART, REP = ROOT / "ml" / "artifacts", ROOT / "data" / "reports"
F2 = make_scorer(fbeta_score, beta=2)

SAFE_REAL = ["https://www.wikipedia.org/wiki/Python", "https://www.google.com/", "https://github.com/pallets/flask",
             "https://www.python.org/downloads/", "https://docs.djangoproject.com/en/5.1/", "https://www.microsoft.com/en-us/windows",
             "https://www.apple.com/iphone/", "https://www.kaspi.kz/shop/", "https://halykbank.kz/about", "https://egov.kz/cms/ru"]
SUSP_RESERVED = ["http://192.0.2.15/account-update", "http://xn--exmplecua.test/secure/login?verify=1",
                 "http://secure-bank-verify.example/login", "http://bit.ly/prize-claimtest", "http://paypa1-login.test/verify",
                 "http://kaspi.example@evil-host.test/login", "http://login.update.google.account-center.test/signin",
                 "http://halyk-bonus-free.invalid:8443/claim", "http://203.0.113.9:8080/bank/login.php?session=abc123", "http://apple-id.confirm-wallet.example//login"]


def metrics(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"accuracy": accuracy_score(y, pred), "precision": precision_score(y, pred, zero_division=0), "recall": recall_score(y, pred),
            "f1": f1_score(y, pred), "f2": fbeta_score(y, pred, beta=2), "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp), "threshold": thr}


def main():
    d = pd.read_csv(ROOT / "data/processed/urls/url_features.csv")
    cols = list(FEATURE_NAMES)
    tr, va, te = (d[d.split == s].reset_index(drop=True) for s in ("train", "val", "test"))
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    cands = {
        "LogisticRegression": (Pipeline([("sc", StandardScaler()), ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))]), {"clf__C": [0.1, 1, 10]}),
        "RandomForest": (Pipeline([("clf", RandomForestClassifier(random_state=42, n_jobs=-1, class_weight="balanced"))]), {"clf__n_estimators": [200, 400], "clf__max_depth": [8, 16, None]}),
        "HistGradientBoosting": (Pipeline([("clf", HistGradientBoostingClassifier(random_state=42))]), {"clf__max_depth": [3, 6], "clf__learning_rate": [0.05, 0.1]}),
    }
    table, fitted = [], {}
    for name, (pipe, grid) in cands.items():
        t0 = time.time()
        gs = GridSearchCV(pipe, grid, scoring=F2, cv=cv, n_jobs=-1).fit(tr[cols], tr.label, groups=tr.family)
        p = gs.predict_proba(va[cols])[:, 1]
        m = metrics(va.label.values, p)
        m.update({"model": name, "best_params": gs.best_params_, "cv_f2": gs.best_score_, "fit_seconds": round(time.time() - t0, 1)})
        table.append(m); fitted[name] = (gs, p)
        print(f"{name:22s} val P={m['precision']:.3f} R={m['recall']:.3f} F2={m['f2']:.3f} AUC={m['roc_auc']:.3f}")
    ok = [m for m in table if m["precision"] >= 0.85] or table
    best = max(ok, key=lambda m: m["f2"])
    gs, p_val = fitted[best["model"]]
    yv = va.label.values
    # t1: наибольший порог, при котором Recall >= 0.95 (ниже t1 — SAFE); t2: наименьший порог, при котором Precision >= 0.95 (от t2 — DANGEROUS)
    grid = np.unique(np.round(p_val, 4))
    t1 = max([t for t in grid if recall_score(yv, p_val >= t) >= 0.95] or [0.2])
    t2 = min([t for t in grid if precision_score(yv, p_val >= t, zero_division=0) >= 0.95] or [0.8])
    if t2 <= t1:
        t2 = min(0.99, t1 + 0.1)
    cat = np.where(p_val < t1, "SAFE", np.where(p_val < t2, "SUSPICIOUS", "DANGEROUS"))
    cat_share = {c: {"n": int((cat == c).sum()), "phish_share": float(yv[cat == c].mean()) if (cat == c).any() else None} for c in ("SAFE", "SUSPICIOUS", "DANGEROUS")}
    print("ВЫБРАНО:", best["model"], "t1=%.3f t2=%.3f" % (t1, t2), cat_share)
    # единственная оценка на test (модель, обученная на train)
    p_te = gs.predict_proba(te[cols])[:, 1]
    test_m = metrics(te.label.values, p_te, 0.5)
    test_m_t1 = metrics(te.label.values, p_te, float(t1))
    kind_recall = te.assign(pred=(p_te >= 0.5).astype(int)).groupby("kind").apply(lambda g: round(float((g.pred == g.label).mean()), 3), include_groups=False).to_dict()
    # важность признаков (permutation на validation)
    pi = permutation_importance(gs.best_estimator_, va[cols], yv, scoring=F2, n_repeats=5, random_state=42, n_jobs=-1)
    imp = sorted(zip(cols, pi.importances_mean), key=lambda t: -t[1])[:10]
    # переобучение на train+val и сохранение
    trva = pd.concat([tr, va], ignore_index=True)
    final = Pipeline(cands[best["model"]][0].steps)
    final.set_params(**best["best_params"]).fit(trva[cols], trva.label)
    joblib.dump({"model": final, "features": cols}, ART / "url_model.joblib")
    # 20 искусственных URL
    chk = pd.DataFrame([extract_url_features(u) for u in SAFE_REAL + SUSP_RESERVED])[cols]
    pc = final.predict_proba(chk)[:, 1]
    def catf(p): return "SAFE" if p < t1 else ("SUSPICIOUS" if p < t2 else "DANGEROUS")
    art20 = [{"url": u, "expected": "safe" if i < 10 else "suspicious", "p_url": round(float(p), 3), "category": catf(p)} for i, (u, p) in enumerate(zip(SAFE_REAL + SUSP_RESERVED, pc))]
    meta = {"version": "1.0.0-synthetic", "algorithm": best["model"], "params": best["best_params"], "features": cols,
            "t1": float(t1), "t2": float(t2), "trained_at": datetime.now(timezone.utc).isoformat(), "real_data_used": False,
            "note": "Обучено только на синтетических URL (.example/.test/.invalid). Метрики НЕ оценивают качество на реальных URL; признак TLD не информативен.",
            "validation_table": table, "category_breakdown_validation": cat_share, "test_metrics_thr0.5_trained_on_train": test_m,
            "test_metrics_at_t1": test_m_t1, "test_accuracy_by_kind": kind_recall,
            "top10_permutation_importance_val": [{"feature": f, "f2_drop": round(float(v), 4)} for f, v in imp],
            "artificial_20_check": art20}
    json.dump(meta, open(ART / "url_model_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("TEST:", {k: round(v, 3) if isinstance(v, float) else v for k, v in test_m.items()})
    print("top10:", [(f, round(float(v), 3)) for f, v in imp])
    print("worst kinds:", sorted(kind_recall.items(), key=lambda t: t[1])[:6])
    for r in art20: print(r["expected"], r["category"], r["p_url"], r["url"][:60])


if __name__ == "__main__":
    main()
