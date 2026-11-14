import copy
import unittest
from ml.risk import compute_risk, level_for, load_config

CFG = {"weights": {"sms": 0.5, "url": 0.3, "se": 0.2}, "se_saturation_groups": 3, "levels": {"medium_min": 35, "high_min": 70},
       "url_t2": 0.5, "overrides": {"code_request_min": 70, "sms_url_combo": {"p_sms_min": 0.8, "min_score": 85}, "url_ip_or_punycode_min": 60},
       "mitigation": {"code_warning_penalty": 20, "apply_only_without_url": True}, "reasons_max": 6, "disclaimer": "d"}


class TestRisk(unittest.TestCase):
    def test_level_boundaries(self):
        self.assertEqual(level_for(34, CFG), ("LOW", "SAFE"))
        self.assertEqual(level_for(35, CFG), ("MEDIUM", "SUSPICIOUS"))
        self.assertEqual(level_for(69, CFG), ("MEDIUM", "SUSPICIOUS"))
        self.assertEqual(level_for(70, CFG), ("HIGH", "FRAUDULENT"))
        self.assertEqual(level_for(0, CFG)[0], "LOW")
        self.assertEqual(level_for(100, CFG)[0], "HIGH")

    def test_all_zero(self):
        r = compute_risk(0.0, None, [], cfg=CFG)
        self.assertEqual(r.score, 0)
        self.assertGreaterEqual(len(r.reasons), 1)
        self.assertTrue(r.recommendation)

    def test_no_url_excludes_url_term(self):
        r = compute_risk(1.0, None, [], cfg=CFG)   # (0.5*1)/(0.5+0.2) = 71.4
        self.assertEqual(r.score, 71)

    def test_formula_with_url(self):
        r = compute_risk(0.5, 0.5, ["URGENCY"], cfg=CFG)   # (0.25+0.15+0.2/3)/(1.0)
        self.assertEqual(r.score, round(100 * (0.25 + 0.15 + 0.2 / 3)))

    def test_se_saturates_at_3_groups(self):
        a = compute_risk(0.0, None, ["A", "B", "C"], cfg=CFG).score
        b = compute_risk(0.0, None, ["A", "B", "C", "D", "E"], cfg=CFG).score
        self.assertEqual(a, b)

    def test_override_code_request(self):
        self.assertEqual(compute_risk(0.0, None, ["CODE_REQUEST"], cfg=CFG).score, 70)

    def test_override_combo(self):
        r = compute_risk(0.8, 0.5, [], cfg=CFG)
        self.assertGreaterEqual(r.score, 85)
        self.assertIn("SMS_URL_COMBO", r.applied_rules)

    def test_override_ip(self):
        self.assertEqual(compute_risk(0.0, 0.1, [], {"has_ip": True}, cfg=CFG).score, 60)

    def test_all_flags_at_once(self):
        r = compute_risk(1.0, 1.0, ["URGENCY", "CODE_REQUEST", "ACCOUNT_BLOCK", "PRIZE"], {"has_ip": True}, cfg=CFG)
        self.assertEqual(r.score, 100)
        self.assertEqual(r.level, "HIGH")
        self.assertLessEqual(len(r.reasons), 6)

    def test_mitigation_only_without_url(self):
        base = compute_risk(1.0, None, [], cfg=CFG).score
        self.assertEqual(compute_risk(1.0, None, [], cfg=CFG, code_warning=True).score, base - 20)
        self.assertEqual(compute_risk(1.0, 0.2, [], cfg=CFG, code_warning=True).score, compute_risk(1.0, 0.2, [], cfg=CFG).score)

    def test_url_only(self):
        r = compute_risk(None, 0.9, [], cfg=CFG, text_present=False)
        self.assertEqual(r.score, 90)

    def test_reasons_sorted_and_capped(self):
        r = compute_risk(0.9, 0.9, [f"G{i}" for i in range(8)] and ["URGENCY", "BANK_CARD", "PRIZE", "ACCOUNT_BLOCK", "AUTHORITY", "SECRECY", "LINK_REQUEST"], cfg=CFG,
                         url_reasons=["Причина 1", "Причина 2"])
        self.assertEqual(len(r.reasons), 6)

    def test_config_change_changes_result_without_code_change(self):
        c2 = copy.deepcopy(CFG)
        c2["weights"] = {"sms": 0.1, "url": 0.1, "se": 0.9}
        self.assertNotEqual(compute_risk(0.9, None, [], cfg=CFG).score, compute_risk(0.9, None, [], cfg=c2).score)

    def test_real_config_loads(self):
        c = load_config()
        self.assertIn("weights", c)
        self.assertEqual(c["levels"]["high_min"], 70)
