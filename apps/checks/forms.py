from django import forms
from django.conf import settings

from ml.url_features import validate_url


class SmsForm(forms.Form):
    text = forms.CharField(label="Текст SMS", widget=forms.Textarea(attrs={"rows": 6, "class": "form-control", "autofocus": True,
                           "placeholder": "Вставьте текст сообщения целиком"}), strip=True)
    save_text = forms.BooleanField(label="Сохранить текст SMS в истории", required=False,
                                   widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["text"].max_length = settings.SMS_MAX_LENGTH
        self.fields["text"].widget.attrs["maxlength"] = settings.SMS_MAX_LENGTH
        self.fields["text"].error_messages["required"] = "Введите текст SMS."

    def clean_text(self):
        t = self.cleaned_data["text"]
        if "\x00" in t:
            raise forms.ValidationError("Текст содержит недопустимые символы.")
        if len(t) > settings.SMS_MAX_LENGTH:
            raise forms.ValidationError(f"Слишком длинный текст: максимум {settings.SMS_MAX_LENGTH} символов.")
        return t


class UrlForm(forms.Form):
    url = forms.CharField(label="Ссылка", strip=True, widget=forms.TextInput(attrs={"class": "form-control form-control-lg font-mono",
                          "placeholder": "например, secure-bank.example/login", "autofocus": True, "autocomplete": "off"}))

    def clean_url(self):
        u = self.cleaned_data["url"]
        if len(u) > settings.URL_MAX_LENGTH:
            raise forms.ValidationError(f"Слишком длинная ссылка: максимум {settings.URL_MAX_LENGTH} символов.")
        if "\x00" in u or any(ch.isspace() for ch in u):
            raise forms.ValidationError("Ссылка не должна содержать пробелов и управляющих символов.")
        v = validate_url(u)    # только разбор строки, без сетевых запросов
        if not v.ok:
            raise forms.ValidationError(v.error)
        return u


class HistoryFilterForm(forms.Form):
    KIND = [("", "Все типы")] + [("SMS", "SMS"), ("URL", "Ссылки")]
    CAT = [("", "Все категории"), ("SAFE", "Безопасно"), ("SUSPICIOUS", "Подозрительно"), ("FRAUDULENT", "Мошенничество")]
    kind = forms.ChoiceField(choices=KIND, required=False, label="Тип", widget=forms.Select(attrs={"class": "form-select"}))
    category = forms.ChoiceField(choices=CAT, required=False, label="Категория", widget=forms.Select(attrs={"class": "form-select"}))
    date_from = forms.DateField(required=False, label="С даты", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    date_to = forms.DateField(required=False, label="По дату", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    min_score = forms.IntegerField(required=False, min_value=0, max_value=100, label="Риск от",
                                   widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0"}))

    def clean(self):
        d = super().clean()
        if d.get("date_from") and d.get("date_to") and d["date_from"] > d["date_to"]:
            raise forms.ValidationError("Дата «с» не может быть позже даты «по».")
        return d
