"""Воспроизводимая генерация синтетических SMS (ru/kk/en): python -m ml.data.generate_sms
Все сообщения искусственные; телефоны/карты вымышленные; URL только на зарезервированных доменах."""
from __future__ import annotations

import csv
import random
import re
from pathlib import Path

from ml.data.sms_templates import T
from ml.data.url_gen import legit_url, phish_url

SEED = 42
TARGET = {"ru": 1250, "kk": 850, "en": 1050}   # бинарные сообщения (50/50)
N_SUSPICIOUS = 60                                # на язык, отдельный класс, не для бинарного обучения
OUT = Path(__file__).resolve().parents[2] / "data" / "synthetic"

NAMES = {
    "ru": "Анна Дима Олег Катя Сергей Марина Игорь Лена Артём Ира Вика Максим Наташа".split(),
    "kk": "Айгүл Нұрлан Дәулет Айнұр Ерлан Мөлдір Асхат Жанар Бақыт Гүлнар Төлеген Салтанат".split(),
    "en": "Anna Dave Mike Kate Sam Emma Jake Lily Tom Nina Ben Zoe Alex".split(),
}
BANKS = {
    "ru": "Каспи Халык Сбербанк Тинькофф Альфа-Банк ForteBank Jusan".split(),
    "kk": "Kaspi Halyk Сбербанк Jusan ForteBank Береке".split(),
    "en": "Chase Barclays HSBC Citi Santander".split(),
}
ORGS = {
    "ru": "Магнит Технодом Aviata Sulpak Wildberries Ozon Аптека-Плюс Лента".split(),
    "kk": "Technodom Sulpak Magnum Aviata Small Kaspi-Магазин Дәріхана".split(),
    "en": "Walmart BestBuy Amazon Zara Uber Spotify Netflix".split(),
}
PLACES = {
    "ru": "Магнит Пятёрочка АЗС Пекарня Аптека Кофейня Ресторан".split(),
    "kk": "Magnum Дәріхана Кофеханасы Дүкен Базар Пекарня".split(),
    "en": "Starbucks Shell Target Walgreens Subway Costco".split(),
}
DATES = {
    "ru": ["12.11", "15.11.2026", "3 декабря", "20 ноября", "01.12", "в пятницу", "в среду"],
    "kk": ["12.11", "15.11.2026", "03.12", "20.11", "01.12"],
    "en": ["Nov 12", "11/15", "Dec 3", "Nov 20", "Monday", "Friday"],
}
GREET = {"ru": ["Здравствуйте!", "Добрый день.", "Привет!", "Внимание:"],
         "kk": ["Сәлеметсіз бе!", "Қайырлы күн.", "Сәлем!", "Назар аударыңыз:"],
         "en": ["Hello!", "Hi,", "Good day.", "Notice:"]}
CLOSE = {"ru": ["Спасибо.", "С уважением.", "Хорошего дня!", "Ответ не требуется."],
         "kk": ["Рахмет.", "Құрметпен.", "Күніңіз жақсы өтсін!", "Жауап қажет емес."],
         "en": ["Thanks.", "Regards.", "Have a nice day!", "No reply needed."]}
MIX = {"ru": ["pls", "ok", "thx", "asap"], "kk": ["срочно", "ok", "спс", "пожалуйста"], "en": ["пжл", "ok", "asap", "plz"]}
EMOJI = ["🙏", "😊", "✅", "❗", "📦", "💳"]
SPECIAL_KK = set("әғқңөұүһі")
SPECIAL_KK |= {c.upper() for c in SPECIAL_KK}


def fill_slots(r, lang, text, ctx):
    def amt():
        n = r.choice([r.randint(5, 99), r.randint(100, 999), r.randint(1000, 99999)])
        if lang == "en":
            return r.choice([f"${n}", f"£{n}", f"{n} USD", f"${n}.{r.randint(10, 99)}"])
        s = f"{n:,}".replace(",", " ")
        return r.choice([f"{s} ₸", f"{s} тг", f"{s} теңге" if lang == "kk" else f"{s} тенге", f"{s} руб" if lang == "ru" else f"{s} ₸"])

    def phone():
        return r.choice([f"+7 7{r.randint(0, 9)}{r.randint(0, 9)} 000 {r.randint(10, 99)} {r.randint(10, 99)}",
                         f"8 7{r.randint(0, 9)}{r.randint(0, 9)} 000 {r.randint(10, 99)} {r.randint(10, 99)}"]) if lang != "en" \
            else f"+1 555 01{r.randint(10, 99)}"

    vals = {
        "name": lambda: r.choice(NAMES[lang]), "bank": lambda: r.choice(BANKS[lang]),
        "org": lambda: r.choice(ORGS[lang]), "place": lambda: r.choice(PLACES[lang]),
        "date": lambda: r.choice(DATES[lang]), "time": lambda: f"{r.randint(7, 22)}:{r.choice(['00', '15', '30', '45'])}",
        "code": lambda: str(r.randint(1000, 999999)), "card4": lambda: f"{r.randint(0, 9999):04d}",
        "num": lambda: str(r.randint(1000, 99999999)), "amt": amt, "phone": phone,
        "handle": lambda: r.choice(["promo", "help", "job", "invest", "support", "cash", "pro"]) + r.choice(["_", ".", ""]) + r.choice(["kz", "24", "online", "team", str(r.randint(1, 999))]),
        "urlsafe": lambda: legit_url(r)[0], "urlgov": lambda: f"https://egov-{r.choice(['portal', 'status', 'docs'])}.example/{r.choice(['status', 'request', 'cabinet'])}/{r.randint(1000, 99999)}",
        "urlphish": lambda: phish_url(r)[0],
        "urlsus": lambda: r.choice([f"https://{r.choice(['lnk.example', 'shrt.test', 'u.example'])}/{r.randint(1000, 99999)}", phish_url(r)[0], legit_url(r)[0]]),
    }
    return re.sub(r"<(\w+)>", lambda m: vals[m.group(1)]() if m.group(1) in vals else m.group(0), text)


def expand(r, tpl):
    return re.sub(r"\{([^{}]*)\}", lambda m: r.choice(m.group(1).split("|")), tpl)


def noise(r, lang, text, flags):
    if r.random() < 0.15:
        text = text.lower(); flags.append("lower")
    if r.random() < 0.10:
        text = text.rstrip(".!?"); flags.append("nopunct")
    if r.random() < 0.12 and len(text) > 12:   # опечатка: перестановка соседних букв в слове
        ws = text.split(" ")
        i = r.randrange(len(ws))
        w = ws[i]
        if len(w) > 3 and "<" not in w and "http" not in w and "@" not in w:
            k = r.randrange(len(w) - 1)
            ws[i] = w[:k] + w[k + 1] + w[k] + w[k + 2:]
            text = " ".join(ws); flags.append("typo")
    if r.random() < 0.07 and lang != "kk":      # цифры вместо букв только для латиницы/ru-латиницы
        m = {"a": "4", "e": "3", "o": "0", "i": "1"} if lang == "en" else {"о": "0", "з": "3"}
        def _leet(w):  # только обычные слова: URL, @handle, коды и числа не трогаем
            if not w.isalpha():
                return w
            return "".join(m.get(c, c) if r.random() < 0.5 else c for c in w)
        text = " ".join(_leet(w) for w in text.split(" ")); flags.append("leet")
    if r.random() < 0.12:
        text = r.choice(GREET[lang]) + " " + text; flags.append("greet")
    if r.random() < 0.12:
        text = text + " " + r.choice(CLOSE[lang]); flags.append("close")
    if r.random() < 0.07:
        text = text + " " + r.choice(MIX[lang]); flags.append("mix")
    if r.random() < 0.05:
        text = text + " " + r.choice(EMOJI); flags.append("emoji")
    if r.random() < 0.03:
        text = text.upper(); flags.append("upper")
    if r.random() < 0.04:
        text = text.replace(" ", "  ", 1); flags.append("dblspace")
    return text


def detect_lang(t):
    if any(c in SPECIAL_KK for c in t):
        return "kk"
    if re.search(r"[а-яА-ЯёЁ]", t):
        return "ru"
    return "en" if re.search(r"[a-zA-Z]", t) else "other"


def main():
    r = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ("ru", "kk", "en"):
        rows, seen = [], set()
        plan = []   # (cls, cat, idx, tpl)
        for cls in ("safe", "fraud"):
            fams = [(k, i, t) for k, v in T.items() if k[0] == lang and k[1] == cls for i, t in enumerate(v)]
            n = TARGET[lang] // 2
            plan += [(cls, *fams[j % len(fams)]) for j in range(n)]
        sus = [(k, i, t) for k, v in T.items() if k[0] == lang and k[1] == "suspicious" for i, t in enumerate(v)]
        plan += [("suspicious", *sus[j % len(sus)]) for j in range(N_SUSPICIOUS)]
        for cls, key, idx, tpl in plan:
            for _ in range(200):
                flags = []
                txt = fill_slots(r, lang, expand(r, tpl), None)
                txt = re.sub(r"\s+([.,!?:])", r"\1", txt).strip()
                txt = noise(r, lang, txt, flags)
                if txt and txt.lower() not in seen:
                    seen.add(txt.lower())
                    break
            else:
                continue
            rows.append({"text": txt, "label": {"safe": 0, "fraud": 1}.get(cls, ""), "class3": cls, "lang": lang,
                         "category": key[2], "family": f"{lang}-{key[1]}-{key[2]}-{idx}", "noise": "+".join(flags),
                         "source": "synthetic"})
        r.shuffle(rows)
        path = OUT / f"sms_{lang}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id", "text", "label", "class3", "lang", "category", "family", "noise", "source"])
            w.writeheader()
            for i, row in enumerate(rows):
                w.writerow({"id": f"{lang}{i:05d}", **row})
        print(lang, len(rows), "->", path)


if __name__ == "__main__":
    main()
