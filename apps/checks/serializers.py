from django.conf import settings
from rest_framework import serializers

from ml.url_features import validate_url

from .models import Check


class SmsAnalyzeSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=settings.SMS_MAX_LENGTH, trim_whitespace=True)
    save_text = serializers.BooleanField(required=False, default=False)

    def validate_text(self, v):
        if "\x00" in v:
            raise serializers.ValidationError("Недопустимые символы.")
        return v


class UrlAnalyzeSerializer(serializers.Serializer):
    url = serializers.CharField(max_length=settings.URL_MAX_LENGTH, trim_whitespace=True)

    def validate_url(self, v):
        r = validate_url(v)     # только разбор строки, сети нет
        if not r.ok:
            raise serializers.ValidationError(r.error)
        return v


class CheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Check
        fields = ["id", "kind", "language", "category", "risk_level", "risk_score", "p_sms", "p_url_max",
                  "urls", "se_groups", "reasons", "recommendation", "disclaimer", "warnings", "applied_rules",
                  "model_versions", "text_saved", "sms_text", "text_length", "created_at"]
        read_only_fields = fields
