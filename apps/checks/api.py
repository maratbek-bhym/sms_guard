"""REST API v1. Всё, кроме health, требует аутентификации (токен или сессия); данные — только владельца."""
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .forms import HistoryFilterForm
from .models import Check
from .serializers import CheckSerializer, SmsAnalyzeSerializer, UrlAnalyzeSerializer
from .services import ModelUnavailable
from .throttles import AnalyzeThrottle, AuthThrottle


def _unavailable(exc):
    return Response({"detail": str(exc) or "Модель недоступна"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class AnalyzeSmsView(APIView):
    throttle_classes = [AnalyzeThrottle]

    def post(self, request):
        s = SmsAnalyzeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            check = services.check_sms(request.user, s.validated_data["text"], s.validated_data["save_text"])
        except ModelUnavailable as e:
            return _unavailable(e)
        data = CheckSerializer(check).data
        if not check.text_saved:   # в ответе на сам запрос полные URL показываем (клиент их и прислал); в БД их нет
            data["urls"] = check.live_urls
        return Response(data, status=status.HTTP_201_CREATED)


class AnalyzeUrlView(APIView):
    throttle_classes = [AnalyzeThrottle]

    def post(self, request):
        s = UrlAnalyzeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            check = services.check_url(request.user, s.validated_data["url"])
        except ModelUnavailable as e:
            return _unavailable(e)
        except ValueError as e:
            return Response({"url": [str(e)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CheckSerializer(check).data, status=status.HTTP_201_CREATED)


class CheckViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = CheckSerializer

    def get_queryset(self):
        qs = Check.objects.filter(user=self.request.user)
        if self.action == "list":
            f = HistoryFilterForm(self.request.query_params)
            if f.is_valid():
                qs = services.filter_checks(qs, f.cleaned_data)
            else:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(f.errors.get_json_data())
        return qs


class StatsView(APIView):
    def get(self, request):
        return Response(services.dashboard_stats(request.user))


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthThrottle]

    def get(self, request):
        h = services.model_health()
        code = status.HTTP_200_OK if h["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response({"status": h["status"], "sms_model": h["sms_model"], "url_model": h["url_model"], "versions": h["versions"]}, status=code)


class TokenView(ObtainAuthToken):
    throttle_classes = [AuthThrottle]
