from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import UserProfile


class RegistrationTests(TestCase):
    def test_registration_page_loads(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

    def test_successful_registration_creates_unverified_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "testuser1",
                "email": "test1@example.com",
                "password1": "StrongTestPass!928",
                "password2": "StrongTestPass!928",
            },
        )

        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username="testuser1")
        profile = UserProfile.objects.get(user=user)

        self.assertEqual(user.email, "test1@example.com")
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password("StrongTestPass!928"))
        self.assertFalse(profile.email_verified)
        self.assertTrue(profile.verification_token)

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "testuser2",
                "email": "test2@example.com",
                "password1": "StrongTestPass!928",
                "password2": "DifferentPass!928",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="testuser2").exists())
        self.assertContains(response, "The passwords do not match.")

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username="existinguser",
            email="duplicate@example.com",
            password="ExistingPass!928",
        )

        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "duplicate@example.com",
                "password1": "StrongTestPass!928",
                "password2": "StrongTestPass!928",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertContains(
            response,
            "An account with this email address already exists.",
        )

    def test_verification_token_is_single_use(self):
        user = User.objects.create_user(
            username="verifyuser",
            email="verify@example.com",
            password="StrongTestPass!928",
        )
        profile = UserProfile.objects.create(
            user=user,
            email_verified=False,
            verification_token="test-verification-token",
        )

        response = self.client.get(
            reverse(
                "verify_email",
                kwargs={"token": "test-verification-token"},
            )
        )

        self.assertEqual(response.status_code, 200)

        profile.refresh_from_db()
        self.assertTrue(profile.email_verified)
        user.refresh_from_db()
        self.assertTrue(user.is_active)  
        self.assertIsNone(profile.verification_token)

        second_response = self.client.get(
            reverse(
                "verify_email",
                kwargs={"token": "test-verification-token"},
            )
        )

        self.assertEqual(second_response.status_code, 400)
    def test_login_page_loads(self):
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")

    def test_unverified_user_cannot_log_in(self):
        from django.contrib.auth.models import User

        User.objects.create_user(
            username="unverified_user",
            email="unverified@example.com",
            password="StrongPass123!",
            is_active=False,
        )

        response = self.client.post(
            "/accounts/login/",
            {
                "username": "unverified_user",
                "password": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_verified_active_user_can_log_in(self):
        from django.contrib.auth.models import User

        User.objects.create_user(
            username="verified_user",
            email="verified@example.com",
            password="StrongPass123!",
            is_active=True,
        )

        response = self.client.post(
            "/accounts/login/",
            {
                "username": "verified_user",
                "password": "StrongPass123!",
            },
        )

        self.assertRedirects(response, "/accounts/register/")
        self.assertTrue(response.wsgi_request.user.is_authenticated)