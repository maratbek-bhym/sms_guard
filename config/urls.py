from django.urls import include, path

urlpatterns = [
    path("accounts/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.checks.api_urls")),
    path("", include("apps.checks.urls")),
]

handler404 = "apps.core.views.error_404"
handler403 = "apps.core.views.error_403"
handler500 = "apps.core.views.error_500"
