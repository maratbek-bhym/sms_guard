import unittest
from ml.url_features import FEATURE_NAMES, explain_url, extract_url_features as ex, validate_url


class TestUrl(unittest.TestCase):
    def test_fixed_keys_order(self):
        for u in ["https://www.example.com/about", "", None, 123, "http://", "ftp://x.example"]:
            self.assertEqual(tuple(ex(u).keys()), FEATURE_NAMES)

    def test_at_least_20_features(self):
        self.assertGreaterEqual(len(FEATURE_NAMES), 20)

    def test_validate_ok_without_scheme(self):
        v = validate_url("example.com/path")
        self.assertTrue(v.ok)
        self.assertTrue(v.normalized.startswith("http://"))

    def test_validate_errors(self):
        self.assertFalse(validate_url("").ok)
        self.assertFalse(validate_url("   ").ok)
        self.assertFalse(validate_url("javascript:alert(1)").ok)
        self.assertFalse(validate_url("ftp://example.com").ok)
        self.assertFalse(validate_url("http://localhost").ok)
        self.assertFalse(validate_url("http://" + "a" * 2050 + ".example").ok)
        self.assertFalse(validate_url("http://exa mple.com").ok)
        self.assertFalse(validate_url("\x00\x01binary").ok)

    def test_ip(self):
        self.assertEqual(ex("http://192.0.2.15/account-update")["has_ip"], 1.0)
        self.assertEqual(ex("http://[2001:db8::1]/x")["has_ip"], 1.0)
        self.assertEqual(ex("https://www.example.com/")["has_ip"], 0.0)

    def test_https_and_port(self):
        self.assertEqual(ex("https://a.example")["is_https"], 1.0)
        self.assertEqual(ex("http://a.example")["is_https"], 0.0)
        self.assertEqual(ex("http://a.example:8080/")["nonstandard_port"], 1.0)
        self.assertEqual(ex("https://a.example:443/")["nonstandard_port"], 0.0)

    def test_at_and_double_slash(self):
        self.assertEqual(ex("http://kaspi.example@evil-host.test/login")["has_at"], 1.0)
        self.assertEqual(ex("http://a.example/x//y")["double_slash_in_path"], 1.0)

    def test_shortener(self):
        self.assertEqual(ex("bit.ly/prize-claimtest")["is_shortener"], 1.0)
        self.assertEqual(ex("https://lnk.example/aB3")["is_shortener"], 1.0)
        self.assertEqual(ex("https://www.example.com/")["is_shortener"], 0.0)

    def test_suspicious_words(self):
        self.assertGreaterEqual(ex("http://secure-bank-verify.example/login")["num_suspicious_words"], 4)

    def test_punycode_and_mixed_script(self):
        self.assertEqual(ex("http://xn--exmplecua.test/secure/login?verify=1")["has_punycode"], 1.0)
        self.assertEqual(ex("http://kaspіbank.test/")["mixed_script"], 1.0)  # кириллическая «і»

    def test_brand_lookalike(self):
        self.assertEqual(ex("http://kaspl.test/")["brand_lookalike"], 1.0)
        self.assertEqual(ex("http://kaspi.test/")["brand_lookalike"], 0.0)

    def test_subdomains_params(self):
        f = ex("https://login-account.example.com/update?a=1&b=2")
        self.assertEqual(f["num_subdomains"], 1.0)
        self.assertEqual(f["num_query_params"], 2.0)

    def test_explain(self):
        r = explain_url(ex("http://192.0.2.15/account-update"))
        self.assertTrue(any("IP-адрес" in x for x in r))
        self.assertEqual(explain_url(ex("")), [])


if __name__ == "__main__":
    unittest.main()
