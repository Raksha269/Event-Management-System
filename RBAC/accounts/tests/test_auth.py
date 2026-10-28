from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


User = get_user_model()


class LoginLockoutTests(TestCase):
    def setUp(self):
        self.password = "CorrectPassword123!"
        self.user = User.objects.create_user(
            username="rajath",
            email="rajath@example.com",
            password=self.password,
        )
        self.url = "/api/auth/login/"

    def login(self, email=None, password=None):
        return self.client.post(
            self.url,
            {
                "email": email or self.user.email,
                "password": password or self.password,
            },
        )

    def test_successful_login(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.json())

    def test_invalid_password_is_rejected(self):
        response = self.login(password="WrongPassword123!")

        self.assertEqual(response.status_code, 401)

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)

    def test_five_failed_attempts_lock_account(self):
        for _ in range(5):
            response = self.login(password="WrongPassword123!")

        self.assertEqual(response.status_code, 401)

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 5)
        self.assertIsNotNone(self.user.locked_until)

        expected_expiry = timezone.now() + timedelta(minutes=15)
        self.assertLessEqual(self.user.locked_until, expected_expiry)

    def test_sixth_attempt_is_rejected_even_with_correct_password(self):
        for _ in range(5):
            self.login(password="WrongPassword123!")

        response = self.login()

        self.assertEqual(response.status_code, 423)

    def test_lockout_expires_and_login_recovers(self):
        self.user.failed_login_attempts = 5
        self.user.locked_until = timezone.now() - timedelta(seconds=1)
        self.user.save()

        response = self.login()

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)
        self.assertIsNone(self.user.locked_until)