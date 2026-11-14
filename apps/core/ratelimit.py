"""Ограничение частоты запросов для веб-страниц (фиксированное окно, счётчики в Django cache).

Для API используется DRF throttling (apps/checks/throttles.py) с теми же лимитами.
Счётчики LocMem живут в памяти процесса — для нескольких процессов нужен общий кэш (Redis/Memcached).
"""
import time
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render


def client_ip(request) -> str:
    # X-Forwarded-For намеренно не учитываем: заголовок подделывается клиентом.
    return request.META.get("REMOTE_ADDR", "unknown")


def hit(scope: str, ident: str):
    """Регистрирует обращение. Возвращает (разрешено, секунд до сброса окна)."""
    limit, window = settings.RATE_LIMITS[scope]
    now = int(time.time())
    bucket = now // window
    key = f"rl:{scope}:{ident}:{bucket}"
    cache.add(key, 0, timeout=window)
    try:
        count = cache.incr(key)
    except ValueError:   # ключ истёк между add и incr
        cache.set(key, 1, timeout=window)
        count = 1
    return count <= limit, window - (now % window)


def rate_limited(scope: str, by: str = "user", methods=("POST",)):
    """Декоратор view. by='user' — по id пользователя, by='ip' — по IP клиента."""
    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method in methods:
                ident = str(request.user.pk) if by == "user" and request.user.is_authenticated else client_ip(request)
                ok, retry = hit(scope, ident)
                if not ok:
                    resp = render(request, "errors/429.html", {"retry_after": retry}, status=429)
                    resp["Retry-After"] = str(retry)
                    return resp
            return view(request, *args, **kwargs)
        return wrapper
    return deco
