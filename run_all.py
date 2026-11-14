#!/usr/bin/env python3
"""Полный запуск пайплайна SMS Guard: python run_all.py [--skip-data] [--skip-train] [--open-data] [--demo-only]

Шаги: тесты -> генерация данных -> проверки/разбиение -> обучение SMS и URL -> калибровка Risk -> тесты -> демо.
Модели обучаются через import (а не `python -m`), чтобы joblib сохранял ссылки на ml.train_sms, а не __main__.
Кроссплатформенно (Windows/Linux/macOS), только стандартная библиотека + requirements.txt."""
import argparse
import importlib
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
DEMO = [
    "Привет! Встречаемся завтра в 18:00 у входа в библиотеку.",
    "Ваш код подтверждения: 4821. Никому не сообщайте этот код.",
    "Ваша карта заблокирована! Срочно подтвердите данные по ссылке: http://secure-bank-verify.example/login",
    "URGENT: Your account will be suspended in 24 hours. Verify now at http://192.0.2.15/account-update",
    "Мама, у меня проблемы, срочно переведи 50 000 на этот номер, потом всё объясню. Никому не говори.",
    "Сотрудник службы безопасности банка: назовите код из SMS для отмены подозрительной операции.",
    "Картаңыз бұғатталды. Жедел түрде мына сілтеме арқылы растаңыз: http://bank-kz-verify.test",
]
DEMO_URLS = ["https://www.example.com/about", "http://xn--exmplecua.test/secure/login?verify=1"]


def step(title):
    print(f"\n=== {title} ===", flush=True)
    return time.time()


def done(t0):
    print(f"--- готово за {time.time() - t0:.1f} с", flush=True)


def run_tests():
    t = step("Модульные тесты (unittest)")
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=ROOT)
    if r.returncode:
        sys.exit("ОШИБКА: тесты не прошли")
    done(t)


def call(module, func="main"):
    getattr(importlib.import_module(module), func)()


def demo():
    from ml.service import analyze_sms, analyze_url
    step("Демонстрация на реальных моделях")
    for m in DEMO:
        r = analyze_sms(m)
        print(f"{r.risk_score:3d} {r.risk_level:6s} {r.category:11s} p_sms={r.p_sms} p_url={r.p_url_max} | {m[:60]}")
    for u in DEMO_URLS:
        r = analyze_url(u)
        print(f"{r.risk_score:3d} {r.risk_level:6s} {r.category:11s} p_url={r.p_url_max} | {u}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-data", action="store_true", help="не генерировать данные заново")
    ap.add_argument("--skip-train", action="store_true", help="не переобучать модели")
    ap.add_argument("--open-data", action="store_true", help="скачать реальные UCI-наборы (нужна сеть; не проверялось)")
    ap.add_argument("--demo-only", action="store_true", help="только демонстрация на готовых моделях")
    a = ap.parse_args()
    if a.demo_only:
        return demo()
    run_tests()
    if a.open_data:
        t = step("Загрузка открытых наборов"); call("ml.data.download_open"); done(t)
    if not a.skip_data:
        t = step("Генерация синтетических данных (seed 42)"); call("ml.data.generate_urls"); call("ml.data.generate_sms"); done(t)
        t = step("Проверки качества, групповое разбиение, отчёты"); call("ml.data.build_datasets"); done(t)
    if not a.skip_train:
        t = step("Обучение SMS-модели"); call("ml.train_sms"); done(t)
        t = step("Обучение URL-модели"); call("ml.train_url"); done(t)
        t = step("Калибровка Risk Score на validation"); call("ml.calibrate_risk"); done(t)
    run_tests()
    demo()
    print("\nГотово. Отчёты: data/reports/, модели: ml/artifacts/, статус: IMPLEMENTATION_STATUS.md")


if __name__ == "__main__":
    main()
