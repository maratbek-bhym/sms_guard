from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("checks", api.CheckViewSet, basename="check")

app_name = "api"
urlpatterns = [
    path("auth/token/", api.TokenView.as_view(), name="token"),
    path("health/", api.HealthView.as_view(), name="health"),
    path("analyze/sms/", api.AnalyzeSmsView.as_view(), name="analyze-sms"),
    path("analyze/url/", api.AnalyzeUrlView.as_view(), name="analyze-url"),
    path("stats/", api.StatsView.as_view(), name="stats"),
    path("", include(router.urls)),
]
