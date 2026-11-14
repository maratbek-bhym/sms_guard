"""Чтение UCI SMS Spam Collection -> DataFrame(id, text, label). НЕ ЗАПУСКАЛСЯ без реального файла."""
from pathlib import Path

import pandas as pd


def load_sms(path):
    path = Path(path)
    for enc in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, sep="\t", header=None, names=["tag", "text"], encoding=enc, quoting=3)
            break
        except UnicodeDecodeError:
            continue
    df["label"] = (df.tag == "spam").astype(int)
    df.insert(0, "id", range(len(df)))
    return df[["id", "text", "label"]]
