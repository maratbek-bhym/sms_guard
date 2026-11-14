from django.urls import path

from . import views

app_name = "checks"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sms/", views.sms_analyzer, name="sms"),
    path("url/", views.url_analyzer, name="url"),
    path("history/", views.history, name="history"),
    path("history/clear/", views.clear_history, name="clear"),
    path("history/<int:pk>/", views.detail, name="detail"),
    path("history/<int:pk>/delete/", views.delete, name="delete"),
]
