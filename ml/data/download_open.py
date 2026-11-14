"""Загрузка открытых наборов (НЕ ЗАПУСКАЛСЯ в среде без сети — проверьте URL и лицензии на страницах UCI).
Использование: python -m ml.data.download_open"""
import hashlib
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sms_open": ("https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip", "https://archive.ics.uci.edu/dataset/228/sms+spam+collection"),
    "url_open": ("https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip", "https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset"),
}


def main():
    for name, (url, page) in SOURCES.items():
        dst = ROOT / "data" / "raw" / name
        dst.mkdir(parents=True, exist_ok=True)
        zpath = dst / "download.zip"
        urllib.request.urlretrieve(url, zpath)
        sha = hashlib.sha256(zpath.read_bytes()).hexdigest()
        zipfile.ZipFile(zpath).extractall(dst)
        (dst / "PASSPORT.txt").write_text(f"source: {page}\nurl: {url}\ndownloaded: {date.today()}\nsha256: {sha}\nlicense: ЗАПОЛНИТЬ по странице источника\n", encoding="utf-8")
        print(name, "ok", sha[:12])


if __name__ == "__main__":
    main()
