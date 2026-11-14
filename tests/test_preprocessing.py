import unittest
from ml.preprocessing import normalize_sms as n


class TestNormalize(unittest.TestCase):
    def test_empty_and_none(self):
        self.assertEqual(n(""), "")
        self.assertEqual(n(None), "")
        self.assertEqual(n("   \t\n "), "")

    def test_only_url(self):
        self.assertEqual(n("http://secure-bank-verify.example/login"), "<url>")
        self.assertEqual(n("bit.ly/abc123"), "<url>")

    def test_url_trailing_punct_kept(self):
        self.assertEqual(n("Зайдите: http://a-b.example/x."), "зайдите: <url>.")

    def test_mixed_case_and_nfkc(self):
        self.assertEqual(n("ＨＥＬＬＯ World"), "hello world")

    def test_cyrillic(self):
        self.assertEqual(n("ПРИВЕТ, Мир"), "привет, мир")

    def test_kazakh_letters_kept(self):
        out = n("Әлем ғажап, қала үлкен ұлы өнер һәм ің і")
        for ch in "әғқңөұүһі":
            self.assertIn(ch, out)

    def test_money(self):
        self.assertEqual(n("Оплатите 350 ₸ сейчас"), "оплатите <money> сейчас")
        self.assertEqual(n("You won $1000!"), "you won <money>!")
        self.assertEqual(n("переведи 50 000 руб"), "переведи <money>")

    def test_phone(self):
        self.assertEqual(n("Звоните +7 700 000 12 34"), "звоните <phone>")

    def test_num_and_email(self):
        self.assertEqual(n("код 4821"), "код <num>")
        self.assertEqual(n("пишите a.b@mail.example"), "пишите <email>")

    def test_emoji_preserved(self):
        self.assertIn("😊", n("Привет 😊"))

    def test_control_chars_and_spaces(self):
        self.assertEqual(n("a\x00b\x07  c\n\nd"), "a b c d")

    def test_pressure_marks_collapsed(self):
        self.assertEqual(n("Срочно!!! Правда???"), "срочно! правда?")

    def test_idempotent_on_tokens(self):
        once = n("Код 4821 по ссылке http://x-y.example")
        self.assertEqual(n(once), once)


if __name__ == "__main__":
    unittest.main()
