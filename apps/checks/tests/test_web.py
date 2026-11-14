import logging
import socket
import tempfile
from unittest import mock

from django.test import Client, override_settings
from django.urls import reverse

from apps.checks.models import Check
from ml.predictor import Predictor

from .base import BENIGN_SMS, FRAUD_SMS, PASSWORD, BaseCase


class SmsAnalyzerTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.login()

    def post_sms(self, text, save=False):
        data = {"text": text}
        if save:
            data["save_text"] = "on"
        return self.client.post(reverse("checks:sms"), data)

    def test_fraud_sms_result_shown(self):
        r = self.post_sms(FRAUD_SMS)
        self.assertEqual(r.status_code, 200)
        c = Check.objects.get()
        self.assertEqual((c.user, c.kind, c.category), (self.alice, "SMS", "FRAUDULENT"))
        self.assertGreaterEqual(c.risk_score, 70)
        self.assertIsNotNone(c.p_sms)
        self.assertContains(r, "Мошенничество")
        self.assertContains(r, "Почему такая оценка")
        self.assertContains(r, f">{c.risk_score}<")

    def test_benign_sms_is_low(self):
        self.post_sms(BENIGN_SMS)
        c = Check.objects.get()
        self.assertEqual(c.risk_level, "LOW")

    def test_text_not_saved_without_consent(self):
        r = self.post_sms(FRAUD_SMS)
        c = Check.objects.get()
        self.assertFalse(c.text_saved)
        self.assertEqual(c.sms_text, "")
        self.assertEqual(c.text_length, len(FRAUD_SMS))
        # ни текста, ни полного URL нет ни в одном поле записи
        blob = repr(list(Check.objects.values()))
        self.assertNotIn("Ваша карта", blob)
        self.assertNotIn("secure-bank-verify.example/login", blob)
        self.assertEqual(c.urls[0]["domain"], "secure-bank-verify.example")
        self.assertNotContains(r, "Ваша карта заблокирована")   # текст не возвращается в форме

    def test_text_saved_with_consent(self):
        self.post_sms(FRAUD_SMS, save=True)
        c = Check.objects.get()
        self.assertTrue(c.text_saved)
        self.assertEqual(c.sms_text, FRAUD_SMS)
        self.assertEqual(c.urls[0]["url"], "http://secure-bank-verify.example/login")

    def test_model_forces_invariant_on_save(self):
        c = Check.objects.create(user=self.alice, kind="SMS", category="SAFE", risk_level="LOW", risk_score=1,
                                 text_saved=False, sms_text="secret")
        c.refresh_from_db()
        self.assertEqual(c.sms_text, "")

    def test_urls_extracted_and_analysed_separately(self):
        r = self.post_sms("Смотрите http://a-bank-login.example/x и www.prize-win.top/claim и 8.8.8.8/pay", save=True)
        c = Check.objects.get()
        self.assertEqual(len(c.urls), 3)
        for u in c.urls:
            self.assertIn(u["category"], ("SAFE", "SUSPICIOUS", "DANGEROUS"))
            self.assertIsNotNone(u["p_url"])
        self.assertContains(r, "Проверить отдельно", count=3)

    def test_links_never_clickable(self):
        r = self.post_sms(FRAUD_SMS, save=True)
        html = r.content.decode()
        self.assertNotIn('href="http://secure-bank', html)
        self.assertNotRegex(html, r'href="https?://')
        self.assertIn("hxxp://secure-bank-verify[.]example/login", html)
        d = self.client.get(reverse("checks:detail", args=[Check.objects.get().pk]))
        self.assertNotRegex(d.content.decode(), r'href="(?:https?|hxxps?)://')

    def test_xss_escaped(self):
        payload = '<script>alert(1)</script><img src=x onerror=alert(2)>'
        self.post_sms(payload, save=True)
        c = Check.objects.get()
        for resp in (self.client.get(reverse("checks:detail", args=[c.pk])), self.client.get(reverse("checks:history"))):
            html = resp.content.decode()
            self.assertNotIn("<script>alert(1)", html)
            self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;script&gt;", self.client.get(reverse("checks:detail", args=[c.pk])).content.decode())

    def test_validation(self):
        for text in ("", "   ", "x" * 2001):
            r = self.post_sms(text)
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, "errorlist")
        self.assertEqual(Check.objects.count(), 0)

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        c.login(username="alice", password=PASSWORD)
        self.assertEqual(c.post(reverse("checks:sms"), {"text": FRAUD_SMS}).status_code, 403)
        self.assertEqual(Check.objects.count(), 0)

    def test_rate_limit(self):
        with override_settings(RATE_LIMITS={"analyze": (3, 60), "auth": (10, 60)}):
            codes = [self.post_sms(BENIGN_SMS).status_code for _ in range(5)]
        self.assertEqual(codes, [200, 200, 200, 429, 429])
        self.assertEqual(Check.objects.count(), 3)

    def test_model_unavailable_shows_error(self):
        with tempfile.TemporaryDirectory() as d:
            Predictor._inst = Predictor(art_dir=d)   # пустая папка: моделей нет
            r = self.post_sms(FRAUD_SMS)
            self.assertEqual(r.status_code, 503)
            self.assertContains(r, "Анализ недоступен", status_code=503)
            self.assertEqual(Check.objects.count(), 0)
            self.assertEqual(self.client.get(reverse("checks:dashboard")).status_code, 200)   # остальное приложение живо

    def test_models_loaded_once(self):
        Predictor.get()
        with mock.patch("ml.predictor.joblib.load", side_effect=AssertionError("повторная загрузка модели")):
            self.post_sms(BENIGN_SMS)
            self.post_sms(FRAUD_SMS)
        self.assertEqual(Check.objects.count(), 2)
        self.assertIs(Predictor.get(), Predictor.get())

    def test_no_network_or_dns(self):
        def boom(*a, **k):
            raise AssertionError("сетевое обращение при анализе")
        with mock.patch.object(socket, "getaddrinfo", boom), mock.patch.object(socket, "gethostbyname", boom), \
                mock.patch.object(socket.socket, "connect", boom):
            self.post_sms(FRAUD_SMS)
            self.client.post(reverse("checks:url"), {"url": "http://secure-bank-verify.example/login"})
        self.assertEqual(Check.objects.count(), 2)

    def test_sms_content_not_logged(self):
        secret = "СЕКРЕТНЫЙ-КОД-7731 http://leak-check.example/path-9917"
        with self.assertLogs(level="DEBUG") as cm:
            logging.getLogger("sms_guard.checks").info("sentinel")   # гарантируем непустой захват
            self.post_sms(secret, save=True)
            self.client.post(reverse("checks:url"), {"url": "http://leak-check.example/path-9917"})
        out = "\n".join(cm.output)
        for needle in ("СЕКРЕТНЫЙ", "7731", "leak-check", "9917"):
            self.assertNotIn(needle, out)
        self.assertIn("check saved", out)


class UrlAnalyzerTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_url_result(self):
        r = self.client.post(reverse("checks:url"), {"url": "http://192.168.4.5/paypal-login.php"})
        self.assertEqual(r.status_code, 200)
        c = Check.objects.get()
        self.assertEqual((c.kind, c.user), ("URL", self.alice))
        self.assertIsNone(c.p_sms)
        self.assertIsNotNone(c.p_url_max)
        self.assertContains(r, "hxxp://192[.]168[.]4[.]5/paypal-login[.]php")
        self.assertNotContains(r, 'href="http://192')

    def test_invalid_urls_rejected(self):
        for u in ("", "ftp://example.com/x", "has space.com", "javascript:alert(1)", "http://", "x" * 2100):
            r = self.client.post(reverse("checks:url"), {"url": u})
            self.assertEqual(r.status_code, 400, u[:30])
        self.assertEqual(Check.objects.count(), 0)

    def test_model_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            Predictor._inst = Predictor(art_dir=d)
            r = self.client.post(reverse("checks:url"), {"url": "http://example.com"})
            self.assertEqual(r.status_code, 503)
            self.assertContains(r, "Анализ недоступен", status_code=503)


class HistoryTests(BaseCase):
    def setUp(self):
        super().setUp()
        for i in range(25):
            Check.objects.create(user=self.alice, kind="SMS" if i % 2 else "URL", category="FRAUDULENT" if i % 5 == 0 else "SAFE",
                                 risk_level="HIGH" if i % 5 == 0 else "LOW", risk_score=90 if i % 5 == 0 else 10)
        Check.objects.create(user=self.bob, kind="SMS", category="FRAUDULENT", risk_level="HIGH", risk_score=99,
                             text_saved=True, sms_text="BOB-PRIVATE-TEXT")
        self.login()

    def test_only_own_records_and_pagination(self):
        r = self.client.get(reverse("checks:history"))
        self.assertEqual(r.context["page"].paginator.count, 25)
        self.assertEqual(len(r.context["page"].object_list), 10)
        self.assertNotContains(r, "BOB-PRIVATE-TEXT")
        r3 = self.client.get(reverse("checks:history") + "?page=3")
        self.assertEqual(len(r3.context["page"].object_list), 5)
        self.assertEqual(self.client.get(reverse("checks:history") + "?page=999").status_code, 200)   # get_page не падает
        self.assertEqual(self.client.get(reverse("checks:history") + "?page=abc").status_code, 200)

    def test_filters(self):
        h = reverse("checks:history")
        self.assertEqual(self.client.get(h + "?category=FRAUDULENT").context["page"].paginator.count, 5)
        self.assertEqual(self.client.get(h + "?kind=SMS").context["page"].paginator.count, 12)
        self.assertEqual(self.client.get(h + "?min_score=50").context["page"].paginator.count, 5)
        self.assertEqual(self.client.get(h + "?kind=URL&category=FRAUDULENT").context["page"].paginator.count, 3)
        self.assertEqual(self.client.get(h + "?date_from=2999-01-01").context["page"].paginator.count, 0)
        self.assertContains(self.client.get(h + "?date_from=2999-01-01"), "Ничего не найдено")

    def test_filter_keeps_in_pagination_links(self):
        r = self.client.get(reverse("checks:history") + "?kind=URL")
        self.assertContains(r, "kind=URL&page=2")

    def test_invalid_filters_do_not_crash_or_inject(self):
        h = reverse("checks:history")
        for q in ("?category=' OR 1=1 --", "?kind=%27%3B DROP TABLE checks_check;--", "?min_score=abc", "?date_from=zzz",
                  "?date_from=2026-02-01&date_to=2026-01-01"):
            r = self.client.get(h + q)
            self.assertEqual(r.status_code, 200, q)
            self.assertEqual(r.context["page"].paginator.count, 25, q)   # некорректные фильтры игнорируются
        self.assertEqual(Check.objects.count(), 26)


class DetailAndDeleteTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.mine = Check.objects.create(user=self.alice, kind="SMS", category="SAFE", risk_level="LOW", risk_score=3,
                                         text_saved=True, sms_text="мой текст", urls=[{"url": "http://a.example", "domain": "a.example", "p_url": .1, "category": "SAFE", "reasons": []}])
        self.theirs = Check.objects.create(user=self.bob, kind="SMS", category="SAFE", risk_level="LOW", risk_score=3,
                                           text_saved=True, sms_text="чужой текст")
        self.login()

    def test_detail_own(self):
        r = self.client.get(reverse("checks:detail", args=[self.mine.pk]))
        self.assertContains(r, "мой текст")
        self.assertContains(r, "Удалить запись")

    def test_detail_other_user_404(self):
        r = self.client.get(reverse("checks:detail", args=[self.theirs.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertNotContains(r, "чужой текст", status_code=404)

    def test_detail_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("checks:detail", args=[self.mine.pk])).status_code, 302)

    def test_delete_own(self):
        url = reverse("checks:delete", args=[self.mine.pk])
        self.assertEqual(self.client.get(url).status_code, 200)       # страница подтверждения, ничего не удаляет
        self.assertTrue(Check.objects.filter(pk=self.mine.pk).exists())
        r = self.client.post(url)
        self.assertRedirects(r, reverse("checks:history"))
        self.assertFalse(Check.objects.filter(pk=self.mine.pk).exists())

    def test_delete_other_user_forbidden(self):
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(reverse("checks:delete", args=[self.theirs.pk])).status_code, 404)
        self.assertTrue(Check.objects.filter(pk=self.theirs.pk).exists())

    def test_delete_requires_csrf(self):
        c = Client(enforce_csrf_checks=True)
        c.login(username="alice", password=PASSWORD)
        self.assertEqual(c.post(reverse("checks:delete", args=[self.mine.pk])).status_code, 403)
        self.assertTrue(Check.objects.filter(pk=self.mine.pk).exists())

    def test_clear_history_only_own(self):
        self.client.post(reverse("checks:clear"))
        self.assertEqual(Check.objects.filter(user=self.alice).count(), 0)
        self.assertEqual(Check.objects.filter(user=self.bob).count(), 1)


class DashboardTests(BaseCase):
    def test_empty_state(self):
        self.login()
        r = self.client.get(reverse("checks:dashboard"))
        self.assertContains(r, "Проверок пока нет")
        self.assertEqual(r.context["stats"]["total"], 0)
        self.assertIsNone(r.context["stats"]["avg_risk"])

    def test_stats_scoped_to_user(self):
        for cat, lvl, score in (("SAFE", "LOW", 10), ("FRAUDULENT", "HIGH", 90), ("SUSPICIOUS", "MEDIUM", 50)):
            Check.objects.create(user=self.alice, kind="SMS", category=cat, risk_level=lvl, risk_score=score)
        Check.objects.create(user=self.alice, kind="URL", category="SAFE", risk_level="LOW", risk_score=20)
        for _ in range(7):
            Check.objects.create(user=self.bob, kind="SMS", category="FRAUDULENT", risk_level="HIGH", risk_score=100)
        self.login()
        s = self.client.get(reverse("checks:dashboard")).context["stats"]
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["by_category"], {"SAFE": 2, "SUSPICIOUS": 1, "FRAUDULENT": 1})
        self.assertEqual(s["by_kind"], {"SMS": 3, "URL": 1})
        self.assertEqual(s["avg_risk"], 42.5)
        self.assertEqual(sum(d["count"] for d in s["per_day"]), 4)
        self.assertEqual(len(s["per_day"]), 14)

    def test_security_headers(self):
        self.login()
        r = self.client.get(reverse("checks:dashboard"))
        self.assertIn("script-src 'self'", r["Content-Security-Policy"])
        self.assertNotIn("unsafe-inline", r["Content-Security-Policy"])
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("<script>", r.content.decode().replace('<script src=', ''))   # нет inline-скриптов
