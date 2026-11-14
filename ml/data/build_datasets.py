"""Проверки качества, групповое разбиение и отчёты: python -m ml.data.build_datasets"""
from __future__ import annotations

import ipaddress
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.tree import DecisionTreeClassifier

from ml.data.generate_sms import detect_lang
from ml.preprocessing import normalize_sms
from ml.url_features import FEATURE_NAMES, extract_url_features, registrable_domain

ROOT = Path(__file__).resolve().parents[2]
SYN, PROC, REP = ROOT / "data" / "synthetic", ROOT / "data" / "processed", ROOT / "data" / "reports"
URL_IN_TEXT = re.compile(r"https?://[^\s<>\"']+|\b[\w\-]+\.(?:example|test|invalid)(?:/\S*)?", re.I)
NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32")]


def url_is_safe(u: str) -> bool:
    try:
        h = urlsplit(u if "://" in u else "http://" + u).hostname or ""
    except ValueError:
        return False
    try:
        ip = ipaddress.ip_address(h)
        return any(ip in n for n in NETS)
    except ValueError:
        return h.endswith((".example", ".test", ".invalid"))


def split_ids(df, y, groups, seed=42):
    sgkf = StratifiedGroupKFold(n_splits=7, shuffle=True, random_state=seed)
    folds = [te for _, te in sgkf.split(df, y, groups)]
    s = np.array(["train"] * len(df), dtype=object)
    s[folds[0]] = "test"
    s[folds[1]] = "val"
    return s


def main():
    stats, issues = {}, []
    # ------------------------------ SMS ------------------------------
    sms = pd.concat([pd.read_csv(SYN / f"sms_{l}.csv", dtype={"label": "float"}) for l in ("ru", "kk", "en")], ignore_index=True)
    stats["sms_raw_rows"] = len(sms)
    stats["sms_empty"] = int((sms.text.fillna("").str.strip() == "").sum())
    sms = sms[sms.text.fillna("").str.strip() != ""].copy()
    sms["text_clean"] = sms.text.map(normalize_sms)
    key = sms.text.str.lower().str.strip()
    stats["sms_exact_dups_removed"] = int(key.duplicated().sum())
    sms = sms[~key.duplicated()].copy()
    # противоречивые метки: одинаковый text_clean, разные метки (только бинарные)
    b = sms[sms.label.notna()]
    g = b.groupby("text_clean").label.nunique()
    contra = set(g[g > 1].index)
    stats["sms_contradictory_label_groups"] = len(contra)
    if contra:
        sms = sms[~sms.text_clean.isin(contra)].copy()
    stats["sms_template_level_duplicates"] = int(sms.text_clean.duplicated().sum())  # одинаковый текст после замены сущностей
    bad_lab = sms[~sms.class3.isin(["safe", "fraud", "suspicious"])]
    stats["sms_bad_class3"] = len(bad_lab)
    stats["sms_label_mismatch"] = int(((sms.class3 == "fraud") != (sms.label == 1)).sum() - (sms.class3 == "suspicious").sum() * 0)
    sms["lang_detected"] = sms.text.map(detect_lang)
    mm = sms[sms.lang != sms.lang_detected]
    stats["sms_lang_mismatch_by_lang"] = mm.lang.value_counts().to_dict()
    # почти дубликаты (cos >= 0.95) внутри/между семействами
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit_transform(sms.text_clean)
    sim = (vec @ vec.T).toarray()
    np.fill_diagonal(sim, 0)
    iu = np.triu_indices_from(sim, 1)
    hi = sim[iu] >= 0.95
    fam = sms.family.values
    same_fam = (fam[iu[0]] == fam[iu[1]])
    stats["sms_near_dup_pairs_same_family"] = int((hi & same_fam).sum())
    stats["sms_near_dup_pairs_cross_family"] = int((hi & ~same_fam).sum())
    # разбиение (только бинарные; suspicious -> eval_only)
    sms["split"] = "eval_only"
    bm = sms.label.notna().values
    bin_df = sms[bm]
    strat = (bin_df.lang + "_" + bin_df.label.astype(int).astype(str)).values
    sms.loc[bm, "split"] = split_ids(bin_df, strat, bin_df.family.values)
    tr_f, te_f, va_f = (set(sms[sms.split == s].family) for s in ("train", "test", "val"))
    assert not (tr_f & te_f) and not (tr_f & va_f) and not (va_f & te_f), "утечка семейств между выборками"
    stats["sms_family_overlap_between_splits"] = 0
    # утечка по сходству: test vs train
    idx = {s: np.where((sms.split == s).values)[0] for s in ("train", "val", "test")}
    mx = sim[np.ix_(idx["test"], idx["train"])].max(axis=1)
    stats["sms_test_to_train_max_cos"] = {"median": float(np.median(mx)), "p95": float(np.quantile(mx, .95)),
                                          "max": float(mx.max()), "n_ge_0.95": int((mx >= .95).sum())}
    stats["sms_split_counts"] = sms.groupby(["split", "lang", "class3"]).size().unstack(fill_value=0).reset_index().to_dict("records")
    stats["sms_families"] = {s: len(set(sms[sms.split == s].family)) for s in ("train", "val", "test", "eval_only")}
    stats["sms_length_chars"] = {f"{l}/{c}": g.text.str.len().describe()[["mean", "min", "max"]].round(1).to_dict() for (l, c), g in sms.groupby(["lang", "class3"])}
    stats["sms_class_balance"] = sms.groupby(["lang", "class3"]).size().unstack(fill_value=0).to_dict("index")
    # безопасность URL в SMS
    viol = [u for t in sms.text for u in URL_IN_TEXT.findall(t) if not url_is_safe(u)]
    stats["sms_url_rule_violations"] = len(viol)
    # сохранение
    out = PROC / "sms"
    sms.drop(columns=[]).to_csv(out / "sms_all.csv", index=False)
    json.dump({s: sms[sms.split == s].id.tolist() for s in ("train", "val", "test", "eval_only")}, open(out / "sms_split.json", "w"))

    # ------------------------------ URL ------------------------------
    u = pd.read_csv(SYN / "urls.csv")
    stats["url_raw_rows"] = len(u)
    u["url_norm"] = u.url.str.strip().str.lower().str.replace(r"^(https?)://", "", regex=True)  # дубли независимо от схемы
    dup = u.duplicated("url")
    stats["url_exact_dups"] = int(dup.sum())
    u = u[~dup].copy()
    stats["url_empty"] = int((u.url.fillna("").str.strip() == "").sum())
    stats["url_label_values"] = sorted(u.label.unique().tolist())
    contra_u = u.groupby("url_norm").label.nunique()
    stats["url_contradictory_labels"] = int((contra_u > 1).sum())
    stats["url_rule_violations"] = int((~u.url.map(url_is_safe)).sum())
    F = pd.DataFrame([extract_url_features(x) for x in u.url])[list(FEATURE_NAMES)]
    u = pd.concat([u.reset_index(drop=True), F], axis=1)
    u["split"] = split_ids(u, u.label.values, u.family.values)
    dtr, dte, dva = (set(u[u.split == s].family) for s in ("train", "test", "val"))
    assert not (dtr & dte) and not (dtr & dva) and not (dva & dte), "домены пересекаются"
    stats["url_domain_overlap_between_splits"] = 0
    stats["url_split_counts"] = u.groupby(["split", "label"]).size().unstack(fill_value=0).reset_index().to_dict("records")
    stats["url_domains"] = {s: len(set(u[u.split == s].family)) for s in ("train", "val", "test")}
    stumps = []
    for f in FEATURE_NAMES:
        x = u[[f]].values
        st = DecisionTreeClassifier(max_depth=1, random_state=0).fit(x, u.label)
        stumps.append((f, float((st.predict(x) == u.label).mean()), float(max(roc_auc_score(u.label, u[f]), 1 - roc_auc_score(u.label, u[f])))))
    stumps.sort(key=lambda t: -t[1])
    stats["url_single_feature_top5"] = [{"feature": a, "stump_accuracy": round(b, 3), "auc": round(c, 3)} for a, b, c in stumps[:5]]
    stats["url_kind_counts"] = u.kind.value_counts().to_dict()
    stats["url_feature_means_by_class"] = u.groupby("label")[["url_length", "num_subdomains", "num_hyphens_host", "has_ip", "is_https", "num_suspicious_words", "host_entropy"]].mean().round(3).to_dict("index")
    out = PROC / "urls"
    u.drop(columns=["url_norm"]).to_csv(out / "url_features.csv", index=False)
    try:
        u.drop(columns=["url_norm"]).to_parquet(out / "url_features.parquet")
    except Exception as e:  # pyarrow отсутствует
        stats["url_parquet"] = f"не создан: {type(e).__name__}"
    json.dump({s: u[u.split == s].id.tolist() for s in ("train", "val", "test")}, open(out / "url_split.json", "w"))

    stats["generated_on"] = str(date.today())
    json.dump(stats, open(REP / "dataset_statistics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(stats, ensure_ascii=False, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
