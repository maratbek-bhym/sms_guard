from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.ratelimit import rate_limited

from . import services
from .forms import HistoryFilterForm, SmsForm, UrlForm
from .models import Check
from .services import ModelUnavailable

MODEL_DOWN = "Анализ временно недоступен: модель не загружена. Обратитесь к администратору."


@login_required
def dashboard(request):
    stats = services.dashboard_stats(request.user)
    recent = Check.objects.filter(user=request.user)[:5]
    chart = {"per_day": stats["per_day"], "by_category": stats["by_category"]}
    return render(request, "checks/dashboard.html", {
        "stats": stats, "recent": recent, "chart_json": chart, "health": services.model_health(),
    })


@login_required
@rate_limited("analyze")
@require_http_methods(["GET", "POST"])
def sms_analyzer(request):
    form = SmsForm(request.POST or None)
    ctx = {"form": form, "health": services.model_health()}
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            check = services.check_sms(request.user, form.cleaned_data["text"], form.cleaned_data["save_text"])
        except ModelUnavailable:
            ctx["model_error"] = MODEL_DOWN
            status = 503
        else:
            ctx.update(check=check, urls=check.live_urls, show_result=True)
            form = SmsForm(initial={"save_text": form.cleaned_data["save_text"]})   # текст из формы не возвращаем
            ctx["form"] = form
    return render(request, "checks/sms.html", ctx, status=status)


@login_required
@rate_limited("analyze")
@require_http_methods(["GET", "POST"])
def url_analyzer(request):
    form = UrlForm(request.POST or None)
    ctx = {"form": form, "health": services.model_health()}
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            check = services.check_url(request.user, form.cleaned_data["url"])
        except ModelUnavailable:
            ctx["model_error"] = MODEL_DOWN
            status = 503
        except ValueError as e:
            form.add_error("url", str(e))
            status = 400
        else:
            ctx.update(check=check, urls=check.urls, show_result=True)
            ctx["form"] = UrlForm()
    elif request.method == "POST":
        status = 400
    return render(request, "checks/url.html", ctx, status=status)


@login_required
def history(request):
    qs = Check.objects.filter(user=request.user)
    form = HistoryFilterForm(request.GET or None)
    if request.GET and form.is_valid():
        qs = services.filter_checks(qs, form.cleaned_data)
    page = Paginator(qs, settings.HISTORY_PAGE_SIZE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "checks/history.html", {
        "form": form, "page": page, "qs": params.urlencode(),
        "filtered": bool(request.GET) and any(v for k, v in request.GET.items() if k != "page"),
    })


@login_required
def detail(request, pk):
    check = get_object_or_404(Check, pk=pk, user=request.user)   # чужая запись -> 404
    return render(request, "checks/detail.html", {"check": check, "urls": check.urls})


@login_required
@require_http_methods(["GET", "POST"])
def delete(request, pk):
    check = get_object_or_404(Check, pk=pk, user=request.user)
    if request.method == "POST":
        check.delete()
        messages.success(request, "Запись удалена.")
        return redirect("checks:history")
    return render(request, "checks/confirm_delete.html", {"check": check})


@login_required
@require_http_methods(["GET", "POST"])
def clear_history(request):
    qs = Check.objects.filter(user=request.user)
    if request.method == "POST":
        n, _ = qs.delete()
        messages.success(request, f"Удалено записей: {n}.")
        return redirect("checks:history")
    return render(request, "checks/confirm_delete.html", {"count": qs.count()})
