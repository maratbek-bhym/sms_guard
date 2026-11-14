"""Калибровка весов/границ Risk Score на validation (модели обучаются только на train). Затем однократный отчёт на test.
Запуск: python -c "import ml.calibrate_risk as c; c.main()" """
from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.naive_bayes import MultinomialNB

import ml.train_sms as ts
from ml.risk import compute_risk, load_config
from ml.rules import find_groups, has_code_warning
from ml.service import _flags, extract_urls
from ml.url_features import FEATURE_NAMES, extract_url_features, validate_url

ROOT = Path(__file__).resolve().parents[1]


def prep(df, sms_model, url_model, cols):
    rows = []
    p_sms = sms_model.predict_proba(df[["text"]])[:, 1]
    for t, p in zip(df.text, p_sms):
        items = []
        for u in extract_urls(t):
            if validate_url(u).ok:
                f = extract_url_features(u)
                items.append({"features": f, "p": float(url_model.predict_proba(pd.DataFrame([f])[cols])[0, 1])})
        rows.append({"p_sms": float(p), "p_url": max((i["p"] for i in items), default=None), "groups": list(find_groups(t)),
                     "flags": _flags(items), "warn": has_code_warning(t)})
    return rows


def evaluate(rows, y, cfg):
    sc = np.array([compute_risk(r["p_sms"], r["p_url"], r["groups"], r["flags"], cfg=cfg, code_warning=r["warn"]).score for r in rows])
    mid, high = cfg["levels"]["medium_min"], cfg["levels"]["high_min"]
    fr, sf = y == 1, y == 0
    return {"recall_med+": float((sc[fr] >= mid).mean()), "recall_high": float((sc[fr] >= high).mean()),
            "safe_high": float((sc[sf] >= high).mean()), "safe_med+": float((sc[sf] >= mid).mean())}


def main():
    d = pd.read_csv(ROOT / "data/processed/sms/sms_all.csv")
    tr, va, te = (d[d.split == s].reset_index(drop=True) for s in ("train", "val", "test"))
    meta = json.loads((ROOT / "ml/artifacts/sms_model_meta.json").read_text(encoding="utf-8"))
    sms_model = ts.build(MultinomialNB(), **({} if meta["features"] == "word+char+manual" else {"use_char": False, "use_manual": False}))
    sms_model.set_params(**meta["params"]).fit(tr[["text"]], tr.label.astype(int).values)
    u = pd.read_csv(ROOT / "data/processed/urls/url_features.csv")
    ut = u[u.split == "train"]
    cols = list(FEATURE_NAMES)
    um = json.loads((ROOT / "ml/artifacts/url_model_meta.json").read_text(encoding="utf-8"))
    pr = um["params"]
    url_model = HistGradientBoostingClassifier(random_state=42, max_depth=pr["clf__max_depth"], learning_rate=pr["clf__learning_rate"]).fit(ut[cols], ut.label)
    rv, rt = prep(va, sms_model, url_model, cols), prep(te, sms_model, url_model, cols)
    yv, yt = va.label.astype(int).values, te.label.astype(int).values
    base = load_config()
    out = []
    for w1, w2, w3, hi, pen in itertools.product((0.2, 0.35, 0.5), (0.2, 0.3, 0.4), (0.2, 0.3, 0.5, 0.8), (70, 80), (0, 20, 35)):
        c = copy.deepcopy(base)
        c["weights"] = {"sms": w1, "url": w2, "se": w3}
        c["levels"]["high_min"] = hi
        c["mitigation"]["code_warning_penalty"] = pen
        out.append({"w": [w1, w2, w3], "high_min": hi, "penalty": pen, **evaluate(rv, yv, c)})
    ok = [o for o in out if o["recall_med+"] >= 0.95]
    ok.sort(key=lambda o: (o["safe_high"], o["safe_med+"]))
    initial = next(o for o in out if o["w"] == [0.5, 0.3, 0.2] and o["high_min"] == 70 and o["penalty"] == 20)
    initial0 = next(o for o in out if o["w"] == [0.5, 0.3, 0.2] and o["high_min"] == 70 and o["penalty"] == 0)
    best = ok[0] if ok else None
    res = {"validation_initial_weights_no_mitigation": initial0, "validation_initial_weights": initial, "validation_top10": ok[:10], "n_variants": len(out), "n_meeting_recall": len(ok)}
    if best:
        c = copy.deepcopy(base)
        c["weights"] = {"sms": best["w"][0], "url": best["w"][1], "se": best["w"][2]}
        c["levels"]["high_min"] = best["high_min"]
        c["mitigation"]["code_warning_penalty"] = best["penalty"]
        res["chosen"] = best
        res["test_chosen_once"] = evaluate(rt, yt, c)
        res["test_initial_weights"] = evaluate(rt, yt, base)
        res["test_chosen_by_language"] = {l: evaluate([r for r, g in zip(rt, te.lang) if g == l], yt[te.lang.values == l], c) for l in ("ru", "kk", "en")}
    json.dump(res, open(ROOT / "data/reports/risk_calibration.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "validation_top10"}, indent=1, ensure_ascii=False))
    print("top5 val:", *[json.dumps(o) for o in ok[:5]], sep="\n")


if __name__ == "__main__":
    main()
