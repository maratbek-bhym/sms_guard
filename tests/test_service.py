import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ml.predictor import ModelUnavailable, Predictor
from ml.service import analyze_sms, analyze_url, extract_urls

ART = Path(__file__).resolve().parents[1] / "ml" / "artifacts"


class TestExtract(unittest.TestCase):
    def test_schemes_and_bare(self):
        u = extract_urls("см www.a-b.example/x, bit.ly/abc и 192.0.2.5/login")
        self.assertEqual(len(u), 3)

    def test_max_three(self):
        self.assertEqual(len(extract_urls("http://a.test/1 http://b.test/2 http://c.test/3 http://d.test/4")), 3)

    def test_no_false_positive_email_or_abbrev(self):
        self.assertEqual(extract_urls("пишите a@b.com, т.е. завтра, e.g. так"), [])

    def test_trailing_punct(self):
        self.assertEqual(extract_urls("Зайдите http://a-b.example/x."), ["http://a-b.example/x"])


class TestService(unittest.TestCase):
    def test_sms_without_url(self):
        r = analyze_sms("Мама, срочно переведи 50 000 на этот номер, никому не говори.")
        self.assertEqual(r.urls, [])
        self.assertIsNone(r.p_url_max)
        self.assertEqual(r.category, "FRAUDULENT")
        self.assertGreaterEqual(len(r.explanation), 1)
        self.assertTrue(r.recommendation and r.disclaimer)

    def test_sms_one_url(self):
        r = analyze_sms("Ваша карта заблокирована! Срочно подтвердите данные: http://secure-bank-verify.example/login")
        self.assertEqual(len(r.urls), 1)
        self.assertIsNotNone(r.p_url_max)
        self.assertEqual(r.category, "FRAUDULENT")

    def test_sms_three_urls_and_cap(self):
        r = analyze_sms("a http://a-x.example/1 b http://b-y.test/2 c http://c-z.test/3 d http://d-w.test/4")
        self.assertEqual(len(r.urls), 3)

    def test_safe_chat(self):
        r = analyze_sms("Привет! Встречаемся завтра в 18:00 у входа в библиотеку.")
        self.assertEqual(r.category, "SAFE")
        self.assertEqual(r.language, "ru")

    def test_kk_has_language_warning(self):
        r = analyze_sms("Сәлем! Ертең сағат 10:00-де кездесеміз бе?")
        self.assertEqual(r.language, "kk")
        self.assertTrue(any("казахск" in w for w in r.warnings))

    def test_only_url(self):
        r = analyze_url("http://xn--exmplecua.test/secure/login?verify=1")
        self.assertEqual(r.type, "URL")
        self.assertIsNone(r.p_sms)
        self.assertGreaterEqual(r.risk_score, 60)

    def test_invalid_url_raises_value_error(self):
        for bad in ("", "javascript:alert(1)", "ftp://x.example", "http://localhost"):
            with self.assertRaises(ValueError):
                analyze_url(bad)

    def test_result_has_spec_fields(self):
        d = analyze_sms("Hello").to_dict()
        for k in ("type", "language", "category", "risk_level", "risk_score", "p_sms", "urls", "features", "explanation",
                  "recommendation", "disclaimer", "model_versions", "created_at"):
            self.assertIn(k, d)

    def test_models_loaded_once(self):
        self.assertIs(Predictor.get(), Predictor.get())


class TestMissingModels(unittest.TestCase):
    def test_missing_files_do_not_crash_and_raise_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            p = Predictor(art_dir=d)
            self.assertFalse(p.health()["sms_model"])
            self.assertEqual(p.health()["status"], "degraded")
            with self.assertRaises(ModelUnavailable):
                analyze_sms("текст", predictor=p)
            with self.assertRaises(ModelUnavailable):
                analyze_url("http://a-b.example/", predictor=p)

    def test_corrupt_model_file(self):
        with tempfile.TemporaryDirectory() as d:
            for f in ART.iterdir():
                shutil.copy(f, d)
            (Path(d) / "url_model.joblib").write_bytes(b"not a model")
            p = Predictor(art_dir=d)
            self.assertIsNone(p.url)
            self.assertIn("url", p.errors)


class TestAbnormalInput(unittest.TestCase):
    def test_binary_long_and_emoji_do_not_crash(self):
        for t in ("\x00\x01\x02\xff" * 20, "а" * 1000, "😀" * 300, "<script>alert(1)</script>", "' OR 1=1 --"):
            r = analyze_sms(t)
            self.assertTrue(0 <= r.risk_score <= 100)
