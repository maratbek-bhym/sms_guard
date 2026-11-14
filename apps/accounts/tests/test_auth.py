from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.checks.tests.base import PASSWORD, BaseCase


class RegistrationTests(BaseCase):
    def test_register_creates_user_and_logs_in(self):
        r = self.client.post(reverse("accounts:register"), {"username": "newbie", "password1": PASSWORD, "password2": PASSWORD})
        self.assertRedirects(r, reverse("checks:dashboard"))
        self.assertTrue(get_user_model().objects.filter(username="newbie").exists())
        self.assertEqual(self.client.get(reverse("checks:dashboard")).status_code, 200)

    def test_password_is_hashed(self):
        self.client.post(reverse("accounts:register"), {"username": "newbie", "password1": PASSWORD, "password2": PASSWORD})
        u = get_user_model().objects.get(username="newbie")
        self.assertNotEqual(u.password, PASSWORD)
        self.assertIn("$", u.password)            # формат «алгоритм$соль$хэш», не открытый текст
        self.assertTrue(u.check_password(PASSWORD))

    def test_duplicate_username_rejected(self):
        r = self.client.post(reverse("accounts:register"), {"username": "alice", "password1": PASSWORD, "password2": PASSWORD})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(get_user_model().objects.filter(username="alice").count(), 1)

    def test_weak_and_mismatched_passwords_rejected(self):
        for p1, p2 in (("12345678", "12345678"), ("short1!", "short1!"), (PASSWORD, PASSWORD + "x"), ("password", "password")):
            r = self.client.post(reverse("accounts:register"), {"username": "weak", "password1": p1, "password2": p2})
            self.assertEqual(r.status_code, 400, p1)
        self.assertFalse(get_user_model().objects.filter(username="weak").exists())

    def test_register_requires_csrf(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("accounts:register"), {"username": "x", "password1": PASSWORD, "password2": PASSWORD})
        self.assertEqual(r.status_code, 403)


class LoginTests(BaseCase):
    def test_login_ok(self):
        r = self.client.post(reverse("accounts:login"), {"username": "alice", "password": PASSWORD})
        self.assertRedirects(r, reverse("checks:dashboard"))

    def test_login_wrong_password(self):
        r = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "nope"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "alert-danger")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_is_post_only(self):
        self.login()
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        r = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(r, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rate_limited(self):
        for _ in range(10):
            self.client.post(reverse("accounts:login"), {"username": "alice", "password": "bad"})
        r = self.client.post(reverse("accounts:login"), {"username": "alice", "password": PASSWORD})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r)

    def test_session_cookie_flags(self):
        r = self.client.post(reverse("accounts:login"), {"username": "alice", "password": PASSWORD})
        c = r.cookies["sessionid"]
        self.assertTrue(c["httponly"])
        self.assertEqual(c["samesite"], "Lax")

    def test_protected_pages_redirect_anonymous(self):
        for name in ("checks:dashboard", "checks:sms", "checks:url", "checks:history"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertTrue(r["Location"].startswith(reverse("accounts:login")), name)
