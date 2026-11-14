"""Фильтры отображения. Ссылки из SMS никогда не превращаются в <a>: выводятся только текстом."""
from django import template

register = template.Library()

LEVEL_CLASS = {"LOW": "low", "MEDIUM": "mid", "HIGH": "high"}
CATEGORY_LABEL = {"SAFE": "Безопасно", "SUSPICIOUS": "Подозрительно", "FRAUDULENT": "Мошенничество",
                  "DANGEROUS": "Опасная"}
LEVEL_LABEL = {"LOW": "Низкий", "MEDIUM": "Средний", "HIGH": "Высокий"}
URL_CLASS = {"SAFE": "low", "SUSPICIOUS": "mid", "DANGEROUS": "high"}
URL_LABEL = {"SAFE": "Безопасная", "SUSPICIOUS": "Подозрительная", "DANGEROUS": "Опасная"}
LANG_LABEL = {"ru": "Русский", "kk": "Казахский", "en": "Английский", "other": "Другой / не определён"}
SE_LABEL = {
    "URGENCY": "Срочность", "MONEY_TRANSFER": "Просьба перевода", "BANK_CARD": "Банк / карта",
    "ACCOUNT_BLOCK": "Угроза блокировки", "PRIZE": "Выигрыш / выплата", "CODE_REQUEST": "Запрос кода",
    "AUTHORITY": "Выдаёт себя за банк или власть", "SECRECY": "Просьба сохранить в тайне", "LINK_REQUEST": "Призыв перейти по ссылке",
}


@register.filter
def level_class(level):
    return LEVEL_CLASS.get(level, "low")


@register.filter
def category_label(cat):
    return CATEGORY_LABEL.get(cat, cat)


@register.filter
def level_label(level):
    return LEVEL_LABEL.get(level, level)


@register.filter
def url_class(cat):
    return URL_CLASS.get(cat, "low")


@register.filter
def url_label(cat):
    return URL_LABEL.get(cat, cat)


@register.filter
def lang_label(code):
    return LANG_LABEL.get(code, code)


@register.filter
def se_label(code):
    return SE_LABEL.get(code, code)


@register.filter
def pct(value):
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "—"


@register.filter
def defang(url):
    """hxxps://evil[.]example — URL показывается как текст и не может быть активной ссылкой даже при копировании."""
    s = str(url or "")
    for a, b in (("https://", "hxxps://"), ("http://", "hxxp://"), ("HTTPS://", "hxxps://"), ("HTTP://", "hxxp://")):
        if s.startswith(a):
            s = b + s[len(a):]
            break
    return s.replace(".", "[.]")
