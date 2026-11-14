import unittest
from ml.rules import RULES, find_groups, has_code_warning


class TestRules(unittest.TestCase):
    def test_at_least_6_groups_with_10_phrases_per_language(self):
        self.assertGreaterEqual(len(RULES), 6)
        for g, spec in RULES.items():
            for lang in ("ru", "kk", "en"):
                self.assertGreaterEqual(len(spec[lang]), 10, (g, lang))

    def test_code_request_ru_en_kk(self):
        self.assertIn("CODE_REQUEST", find_groups("Назовите код из SMS для отмены операции"))
        self.assertIn("CODE_REQUEST", find_groups("Please read out the code we sent you"))
        self.assertIn("CODE_REQUEST", find_groups("Оған картаның артындағы үш таңбалы кодты айтыңыз"))

    def test_legit_otp_is_not_code_request(self):
        t = "Ваш код подтверждения: 4821. Никому не сообщайте этот код."
        self.assertNotIn("CODE_REQUEST", find_groups(t))
        self.assertTrue(has_code_warning(t))

    def test_plain_chat_has_no_groups(self):
        self.assertEqual(find_groups("Привет! Встречаемся завтра в 18:00"), {})

    def test_block_urgency(self):
        g = find_groups("Ваша карта заблокирована! Срочно подтвердите данные")
        self.assertIn("ACCOUNT_BLOCK", g)
        self.assertIn("URGENCY", g)

    def test_empty(self):
        self.assertEqual(find_groups(""), {})
        self.assertEqual(find_groups(None), {})
