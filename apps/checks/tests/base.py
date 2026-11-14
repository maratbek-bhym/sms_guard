from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from ml.predictor import Predictor

FRAUD_SMS = "Ваша карта заблокирована! Срочно подтвердите данные: http://secure-bank-verify.example/login"
BENIGN_SMS = "Привет, встречаемся в 7 у кино"
PASSWORD = "Zx9!kQ-tr41w"


class BaseCase(TestCase):
    def setUp(self):
        cache.clear()   # счётчики rate-limit не должны протекать между тестами
        User = get_user_model()
        self.alice = User.objects.create_user("alice", password=PASSWORD)
        self.bob = User.objects.create_user("bob", password=PASSWORD)

    def tearDown(self):
        Predictor.reset()
        cache.clear()

    def login(self, user="alice"):
        self.assertTrue(self.client.login(username=user, password=PASSWORD))
