from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

from apps.core.ratelimit import rate_limited

from .forms import LoginForm, RegisterForm


@method_decorator(rate_limited("auth", by="ip"), name="dispatch")
class SignInView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


@rate_limited("auth", by="ip")
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("checks:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Аккаунт создан. Можно проверить первое сообщение.")
        return redirect("checks:dashboard")
    return render(request, "registration/register.html", {"form": form}, status=400 if request.method == "POST" else 200)
