import tempfile

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.checks.models import Check
from apps.checks.throttles import AnalyzeThrottle
from ml.predictor import Predictor

from .base import BENIGN_SMS, FRAUD_SMS, PASSWORD, BaseCase


class ApiBase(BaseCase):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.token = Token.objects.create(user=self.alice)
        self.auth = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}

    def post(self, name, data, **kw):
        return self.api.post(reverse(name), data, format="json", **self.auth, **kw)


class AuthApiTests(ApiBase):
    def test_token_obtain(self):
        r = APIClient().post(reverse("api:token"), {"username": "alice", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["token"], self.token.key)
        self.assertEqual(APIClient().post(reverse("api:token"), {"username": "alice", "password": "bad"}, format="json").status_code, 400)

    def test_token_obtain_throttled(self):
        for _ in range(10):
            APIClient().post(reverse("api:token"), {"username": "alice", "password": "bad"}, format="json")
        self.assertEqual(APIClient().post(reverse("api:token"), {"username": "alice", "password": PASSWORD}, format="json").status_code, 429)

    def test_anonymous_rejected(self):
        c = APIClient()
        self.assertEqual(c.post(reverse("api:analyze-sms"), {"text": "hi"}, format="json").status_code, 401)
        self.assertEqual(c.post(reverse("api:analyze-url"), {"url": "http://a.example"}, format="json").status_code, 401)
        self.assertEqual(c.get(reverse("api:check-list")).status_code, 401)
        self.assertEqual(c.get(reverse("api:stats")).status_code, 401)
        self.assertEqual(Check.objects.count(), 0)

    def test_invalid_token(self):
        r = APIClient().get(reverse("api:check-list"), HTTP_AUTHORIZATION="Token deadbeef")
        self.assertEqual(r.status_code, 401)

    def test_session_auth_requires_csrf(self):
        c = APIClient(enforce_csrf_checks=True)
        c.login(username="alice", password=PASSWORD)
        self.assertEqual(c.post(reverse("api:analyze-sms"), {"text": "hi"}, format="json").status_code, 403)


class AnalyzeApiTests(ApiBase):
    def test_analyze_sms(self):
        r = self.post("api:analyze-sms", {"text": FRAUD_SMS, "save_text": False})
        self.assertEqual(r.status_code, 201)
        d = r.json()
        self.assertEqual(d["kind"], "SMS")
        self.assertEqual(d["category"], "FRAUDULENT")
        self.assertTrue(0 <= d["risk_score"] <= 100)
        self.assertTrue(d["reasons"])
        self.assertEqual(d["urls"][0]["domain"], "secure-bank-verify.example")
        self.assertFalse(d["text_saved"])
        self.assertEqual(d["sms_text"], "")
        self.assertEqual(Check.objects.get().user, self.alice)

    def test_analyze_sms_save_text(self):
        d = self.post("api:analyze-sms", {"text": BENIGN_SMS, "save_text": True}).json()
        self.assertTrue(d["text_saved"])
        self.assertEqual(d["sms_text"], BENIGN_SMS)

    def test_save_text_defaults_to_false(self):
        d = self.post("api:analyze-sms", {"text": BENIGN_SMS}).json()
        self.assertFalse(d["text_saved"])
        self.assertEqual(Check.objects.get().sms_text, "")

    def test_analyze_sms_validation(self):
        for payload in ({}, {"text": ""}, {"text": "   "}, {"text": "x" * 2001}, {"text": None}):
            r = self.post("api:analyze-sms", payload)
            self.assertEqual(r.status_code, 400, payload)
        self.assertEqual(Check.objects.count(), 0)

    def test_analyze_url(self):
        r = self.post("api:analyze-url", {"url": "http://192.168.4.5/paypal-login.php"})
        self.assertEqual(r.status_code, 201)
        d = r.json()
        self.assertEqual(d["kind"], "URL")
        self.assertIsNone(d["p_sms"])
        self.assertIn(d["urls"][0]["category"], ("SAFE", "SUSPICIOUS", "DANGEROUS"))

    def test_analyze_url_validation(self):
        for u in ("", "ftp://x.example", "a b.com", "javascript:alert(1)", "x" * 3000, None):
            self.assertEqual(self.post("api:analyze-url", {"url": u}).status_code, 400, str(u)[:20])
        self.assertEqual(Check.objects.count(), 0)

    def test_503_when_model_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            Predictor._inst = Predictor(art_dir=d)
            r1 = self.post("api:analyze-sms", {"text": FRAUD_SMS})
            r2 = self.post("api:analyze-url", {"url": "http://a.example"})
            self.assertEqual((r1.status_code, r2.status_code), (503, 503))
            self.assertIn("detail", r1.json())
            self.assertEqual(self.api.get(reverse("api:health")).status_code, 503)
            self.assertEqual(self.api.get(reverse("api:check-list"), **self.auth).status_code, 200)   # история работает
        self.assertEqual(Check.objects.count(), 0)

    def test_health_ok_and_public(self):
        r = APIClient().get(reverse("api:health"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertNotIn("errors", r.json())

    def test_throttle_30_per_minute_default(self):
        self.assertEqual(AnalyzeThrottle.THROTTLE_RATES["analyze"], "30/min")

    def test_throttling(self):
        from unittest.mock import patch
        with patch.dict(AnalyzeThrottle.THROTTLE_RATES, {"analyze": "3/min"}):
            codes = [self.post("api:analyze-sms", {"text": BENIGN_SMS}).status_code for _ in range(5)]
        self.assertEqual(codes, [201, 201, 201, 429, 429])


class ChecksApiTests(ApiBase):
    def setUp(self):
        super().setUp()
        self.mine = [Check.objects.create(user=self.alice, kind="SMS", category="FRAUDULENT" if i < 3 else "SAFE",
                                          risk_level="HIGH" if i < 3 else "LOW", risk_score=90 if i < 3 else 5) for i in range(25)]
        self.bobs = Check.objects.create(user=self.bob, kind="SMS", category="SAFE", risk_level="LOW", risk_score=1,
                                         text_saved=True, sms_text="BOB-PRIVATE")

    def get(self, name, *a, **q):
        return self.api.get(reverse(name, args=a), q, **self.auth)

    def test_list_only_own_and_paginated(self):
        d = self.get("api:check-list").json()
        self.assertEqual(d["count"], 25)
        self.assertEqual(len(d["results"]), 20)
        self.assertNotIn("BOB-PRIVATE", str(d))
        self.assertEqual(len(self.get("api:check-list", page=2).json()["results"]), 5)

    def test_list_filters(self):
        self.assertEqual(self.get("api:check-list", category="FRAUDULENT").json()["count"], 3)
        self.assertEqual(self.get("api:check-list", min_score=50).json()["count"], 3)
        self.assertEqual(self.get("api:check-list", kind="URL").json()["count"], 0)
        self.assertEqual(self.get("api:check-list", category="bogus").status_code, 400)

    def test_retrieve_own_and_other(self):
        self.assertEqual(self.get("api:check-detail", self.mine[0].pk).status_code, 200)
        self.assertEqual(self.get("api:check-detail", self.bobs.pk).status_code, 404)

    def test_delete_own_and_other(self):
        r = self.api.delete(reverse("api:check-detail", args=[self.mine[0].pk]), **self.auth)
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Check.objects.filter(pk=self.mine[0].pk).exists())
        r = self.api.delete(reverse("api:check-detail", args=[self.bobs.pk]), **self.auth)
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Check.objects.filter(pk=self.bobs.pk).exists())

    def test_cannot_modify_via_api(self):
        pk = self.mine[0].pk
        for method in (self.api.put, self.api.patch):
            self.assertEqual(method(reverse("api:check-detail", args=[pk]), {"risk_score": 0}, format="json", **self.auth).status_code, 405)
        self.assertEqual(self.api.post(reverse("api:check-list"), {}, format="json", **self.auth).status_code, 405)

    def test_stats(self):
        d = self.get("api:stats").json()
        self.assertEqual(d["total"], 25)
        self.assertEqual(d["by_category"]["FRAUDULENT"], 3)
