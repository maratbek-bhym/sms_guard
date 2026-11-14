from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models


class Check(models.Model):
    """Результат одной проверки. Текст SMS хранится только при согласии пользователя (text_saved)."""

    class Kind(models.TextChoices):
        SMS = "SMS", "SMS"
        URL = "URL", "Ссылка"

    class Category(models.TextChoices):
        SAFE = "SAFE", "Безопасно"
        SUSPICIOUS = "SUSPICIOUS", "Подозрительно"
        FRAUDULENT = "FRAUDULENT", "Мошенничество"

    class Level(models.TextChoices):
        LOW = "LOW", "Низкий"
        MEDIUM = "MEDIUM", "Средний"
        HIGH = "HIGH", "Высокий"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="checks")
    kind = models.CharField(max_length=3, choices=Kind.choices)
    language = models.CharField(max_length=8, blank=True)
    category = models.CharField(max_length=12, choices=Category.choices)
    risk_level = models.CharField(max_length=6, choices=Level.choices)
    risk_score = models.PositiveSmallIntegerField(validators=[MaxValueValidator(100)])
    p_sms = models.FloatField(null=True, blank=True)
    p_url_max = models.FloatField(null=True, blank=True)

    text_saved = models.BooleanField(default=False, help_text="Пользователь согласился сохранить текст SMS")
    sms_text = models.TextField(blank=True, default="")
    text_length = models.PositiveIntegerField(default=0)

    urls = models.JSONField(default=list)
    se_groups = models.JSONField(default=list)
    reasons = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
    applied_rules = models.JSONField(default=list)
    model_versions = models.JSONField(default=dict)
    recommendation = models.TextField(blank=True)
    disclaimer = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):   # без содержимого SMS
        return f"Check#{self.pk} {self.kind} {self.category} {self.risk_score}"

    def save(self, *args, **kwargs):
        if not self.text_saved:
            self.sms_text = ""   # инвариант: без согласия текст не хранится
        super().save(*args, **kwargs)

    @property
    def main_url(self):
        return self.urls[0] if self.urls else None
