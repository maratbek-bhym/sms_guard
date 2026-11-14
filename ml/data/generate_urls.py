"""Воспроизводимая генерация синтетического набора URL: python -m ml.data.generate_urls"""
from __future__ import annotations

import csv
import random
from pathlib import Path

from ml.data.url_gen import legit_url, phish_url
from ml.url_features import registrable_domain
from urllib.parse import urlsplit

SEED, N_PER_CLASS = 42, 6000
OUT = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "urls.csv"


def main():
    r = random.Random(SEED)
    rows, seen = [], set()
    for label, gen in ((0, legit_url), (1, phish_url)):
        n = 0
        while n < N_PER_CLASS:
            u, kind = gen(r)
            if u in seen:
                continue
            seen.add(u)
            host = urlsplit(u).hostname or ""
            rows.append({"url": u, "label": label, "kind": kind, "source": "synthetic",
                         "family": registrable_domain(host)})
            n += 1
    r.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "url", "label", "kind", "source", "family"])
        w.writeheader()
        for i, row in enumerate(rows):
            w.writerow({"id": i, **row})
    print(f"{len(rows)} URL -> {OUT}")


if __name__ == "__main__":
    main()
