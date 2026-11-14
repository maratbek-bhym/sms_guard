"""Генератор синтетических URL. Только зарезервированные TLD (.example/.test/.invalid),
адреса TEST-NET (RFC 5737) и 2001:db8::/32. URL никогда не открываются и не резолвятся.
Один и тот же набор TLD используется для обоих классов, чтобы TLD не определял класс."""
from __future__ import annotations

import random
import string

WORDS = ("green blue north river pixel cloud maple stone urban delta alpha orbit market studio atlas nova "
         "craft bright fresh swift harbor summit forest lumen quartz prime vista terra cedar amber altyn "
         "steppe tau silk nomad aqua sun metro cafe books garden health travel tech media sport film "
         "learn city grand royal lotus pearl iron copper").split()
BRANDS = ("kaspi halyk sberbank tinkoff alfabank forte jusan paypal google apple microsoft amazon facebook "
          "instagram netflix dhl fedex kazpost egov telegram whatsapp binance chase wellsfargo barclays hsbc").split()
KEYWORDS = "login verify secure account update confirm bank wallet billing support auth payment bonus gift refund".split()
TLDS = ("example", "test", "invalid")
TLD_W = (0.5, 0.35, 0.15)
SHORT_HOSTS = ("lnk.example", "shrt.test", "go-link.test", "sho.invalid", "tiny-link.test", "u.example",
               "short.invalid", "jmp.test")
TESTNETS = ("192.0.2.", "198.51.100.", "203.0.113.")


def _tld(r):
    return r.choices(TLDS, TLD_W)[0]


def _token(r, lo=8, hi=24):
    return "".join(r.choices(string.ascii_letters + string.digits, k=r.randint(lo, hi)))


def _slug(r):
    return "-".join(r.sample(WORDS, r.randint(2, 4)))


def _company(r):
    a, b = r.sample(WORDS, 2)
    name = r.choice([a + b, a + "-" + b, a + b + str(r.randint(1, 99)), a])
    return name


def _ip(r):
    if r.random() < 0.12:
        return "[2001:db8::%x]" % r.randint(1, 0xffff)
    return r.choice(TESTNETS) + str(r.randint(1, 254))


def _typo(r, s):
    i = r.randrange(len(s))
    k = r.random()
    if k < 0.3 and len(s) > 4:
        return s[:i] + s[i + 1:]
    if k < 0.6:
        return s[:i] + r.choice("0123456789".replace(s[i], "") if s[i].isdigit() else {"o": "0", "i": "1", "l": "1", "a": "4", "e": "3"}.get(s[i], r.choice(string.ascii_lowercase))) + s[i + 1:]
    return s[:i] + s[i] * 2 + s[i + 1:]


def _scheme(r, p_https):
    return "https://" if r.random() < p_https else "http://"


def _port(r, p):
    return ":" + r.choice(["8080", "8443", "8081", "3000", "9000", "2083"]) if r.random() < p else ""


def _legit_path(r):
    n = r.randint(1, 99999)
    opts = [
        "/", "", "/about", "/contact", f"/products/{n}", f"/news/2026/{r.randint(1, 12)}/{_slug(r)}",
        f"/docs/{_slug(r)}.html", f"/blog/{_slug(r)}", f"/catalog/{r.choice(WORDS)}/{r.choice(WORDS)}?page={r.randint(1, 30)}&sort={r.choice(['price', 'name'])}",
        "/account/login", "/account/settings", "/support/verify-email", f"/search?q={r.choice(WORDS)}+{r.choice(WORDS)}",
        f"/user/profile/{n}", f"/download/report-{n}.pdf", f"/orders/{n}/track", f"/reset/{_token(r, 16, 32)}",
        f"/invite/{_token(r, 12, 20)}", f"/s/{_token(r, 10, 16)}", "/login?continue=/home", "/payment/receipt?id=%d" % n,
        f"/a/b/c/d/{_slug(r)}/index.html", f"/shop/{r.choice(WORDS)}?utm_source=sms&utm_medium=notice&ref={_token(r, 6, 10)}",
    ]
    return r.choice(opts)


def _phish_path(r):
    n = r.randint(1, 99999)
    opts = [
        "/login", f"/verify/{_token(r)}", f"/secure/update?id={_token(r, 8, 14)}", "/account/confirm", f"/pay/{n}",
        f"/p/{_token(r, 8, 16)}", f"/{_token(r, 6, 12)}", "/auth/signin?redirect=%2Fhome", f"/bank/login.php?session={_token(r)}&user={n}",
        "/", "/update", f"/claim/{n}", f"/index.php?id={n}", f"/{_slug(r)}", f"/track/{n}", f"/login/{_token(r, 6, 10)}?next=/cabinet",
        f"/s/{_token(r, 10, 16)}", f"/docs/{_slug(r)}.html", f"/about", "/account/settings", "//login", f"/a//b/{_token(r, 6, 10)}",
        f"/reset/{_token(r, 16, 32)}", "/login?continue=/home",
    ]
    return r.choice(opts)


def legit_url(r: random.Random):
    k = r.choices(
        ["plain", "www", "sub", "brand", "brand_sub", "hard_kw", "port", "ip", "short", "idn", "long", "token_path"],
        [22, 14, 14, 8, 8, 10, 4, 2, 5, 2, 6, 5])[0]
    t, sch = _tld(r), None
    if k == "plain":
        u = f"{_scheme(r, 0.85)}{_company(r)}.{t}{_legit_path(r)}"
    elif k == "www":
        u = f"{_scheme(r, 0.9)}www.{_company(r)}.{t}{_legit_path(r)}"
    elif k == "sub":
        u = f"{_scheme(r, 0.9)}{r.choice(['shop', 'app', 'docs', 'mail', 'blog', 'help', 'static', 'cdn'])}.{_company(r)}.{t}{_legit_path(r)}"
    elif k == "brand":
        u = f"{_scheme(r, 0.95)}www.{r.choice(BRANDS)}.{t}{_legit_path(r)}"
    elif k == "brand_sub":
        u = f"{_scheme(r, 0.95)}{r.choice(['pay', 'online', 'accounts', 'secure', 'id', 'my'])}.{r.choice(BRANDS)}.{t}{_legit_path(r)}"
    elif k == "hard_kw":
        u = f"{_scheme(r, 0.9)}{r.choice(['accounts', 'secure', 'login', 'auth', 'support', 'billing'])}.{_company(r)}.{t}/{r.choice(['login', 'verify', 'account/update', 'secure/payment', 'auth/confirm'])}?continue=/home"
    elif k == "port":
        u = f"{_scheme(r, 0.5)}{_company(r)}.{t}:{r.choice(['8080', '8443', '3000'])}{_legit_path(r)}"
    elif k == "ip":
        u = f"http://{_ip(r)}:{r.choice(['8080', '3000', '9000', '80'])}/{r.choice(['status', 'admin', 'metrics', 'health'])}"
    elif k == "short":
        u = f"https://{r.choice(SHORT_HOSTS)}/{_token(r, 5, 8)}"
    elif k == "idn":
        u = f"https://xn--{''.join(r.choices(string.ascii_lowercase + string.digits, k=r.randint(8, 14)))}.{t}{_legit_path(r)}"
    elif k == "long":
        u = f"{_scheme(r, 0.9)}www.{_company(r)}.{t}/" + "/".join(_slug(r) for _ in range(r.randint(3, 6))) + f"?id={r.randint(1, 99999)}&lang={r.choice(['ru', 'kk', 'en'])}&utm_campaign={_slug(r)}"
    else:
        u = f"{_scheme(r, 0.9)}{_company(r)}.{t}/{r.choice(['s', 'u', 'r', 'files'])}/{_token(r, 12, 28)}"
    return u, "legit_" + k


def phish_url(r: random.Random):
    k = r.choices(
        ["brand_kw", "brand_typo", "brand_sub", "kw_host", "ip", "punycode", "userinfo", "port", "short",
         "deep_sub", "no_kw", "params", "long", "brand_mixed", "plain_like"],
        [12, 10, 8, 10, 6, 5, 4, 4, 6, 6, 12, 5, 4, 3, 10])[0]
    t, b = _tld(r), r.choice(BRANDS)
    kw = r.choice(KEYWORDS)
    sch = _scheme(r, 0.7)
    if k == "brand_kw":
        u = f"{sch}{b}-{kw}.{t}{_phish_path(r)}"
    elif k == "brand_typo":
        u = f"{sch}{_typo(r, b)}{r.choice(['', '-' + r.choice(KEYWORDS), str(r.randint(1, 99))])}.{t}{_phish_path(r)}"
    elif k == "brand_sub":
        u = f"{sch}{b}.{r.choice(KEYWORDS)}-{r.choice(WORDS)}.{t}{_phish_path(r)}"
    elif k == "kw_host":
        u = f"{sch}{kw}-{_company(r)}.{t}{_phish_path(r)}"
    elif k == "ip":
        u = f"http://{_ip(r)}{_phish_path(r)}"
    elif k == "punycode":
        u = f"{sch}xn--{''.join(r.choices(string.ascii_lowercase + string.digits, k=r.randint(8, 14)))}.{t}{_phish_path(r)}"
    elif k == "userinfo":
        u = f"{sch}{b}.{t}@{_company(r)}.{t}{_phish_path(r)}"
    elif k == "port":
        u = f"{sch}{_company(r)}.{t}:{r.choice(['8080', '8443', '8081', '2083'])}{_phish_path(r)}"
    elif k == "short":
        u = f"{sch}{r.choice(SHORT_HOSTS)}/{_token(r, 5, 8)}"
    elif k == "deep_sub":
        u = f"{sch}{r.choice(KEYWORDS)}.{r.choice(WORDS)}.{b}.{_company(r)}.{t}{_phish_path(r)}"
    elif k == "no_kw":
        u = f"{sch}{_company(r)}{r.randint(10, 9999)}.{t}/{_token(r, 6, 14)}"
    elif k == "params":
        u = f"{sch}{_company(r)}.{t}/?" + "&".join(f"{p}={_token(r, 4, 10)}" for p in r.sample(["id", "session", "token", "ref", "user", "redirect", "cid"], r.randint(3, 5)))
    elif k == "long":
        u = f"{sch}{_company(r)}-{kw}.{t}/" + "/".join(_token(r, 5, 12) for _ in range(r.randint(3, 6))) + f"?{r.choice(['a', 'q', 'id'])}={_token(r, 20, 40)}"
    elif k == "brand_mixed":
        u = f"{sch}{b[:-1]}\u0456{r.choice(['', '-' + kw])}.{t}{_phish_path(r)}"  # кириллическая «і» вместо латинской
    else:  # plain_like: внешне обычный адрес
        u = f"{sch}{'www.' if r.random() < .3 else ''}{_company(r)}.{t}{_legit_path(r)}"
    return u, "phish_" + k
