"""UI checks for EMS-F-005: role-aware nav, denial pages, role-change screen."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.roles import Role

User = get_user_model()


def mk(role, name=None):
    name = name or role
    return User.objects.create_user(name, f"{name}@x.com", "pw12345!", role=role)


class NavTests(TestCase):
    def test_nav_differs_by_role(self):
        expect = {Role.ATTENDEE: "My registrations", Role.ORGANIZER: "Create event",
                  Role.ADMINISTRATOR: "Users &amp; roles"}
        for role, label in expect.items():
            self.client.force_login(mk(role))
            html = self.client.get(reverse("ui:overview")).content.decode()
            self.assertIn(label, html)
            for other_role, other in expect.items():
                if other_role != role:
                    self.assertNotIn(f">{other}<", html)
            self.assertIn("Skip to content", html)
            self.client.logout()

    def test_anonymous_overview_redirects_to_login(self):
        r = self.client.get(reverse("ui:overview"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])


class DenialPageTests(TestCase):
    def test_non_admin_sees_403_page_with_recovery_link(self):
        for role in (Role.ATTENDEE, Role.ORGANIZER):
            self.client.force_login(mk(role))
            r = self.client.get(reverse("ui:users"))
            self.assertEqual(r.status_code, 403)
            self.assertContains(r, "Back to your overview", status_code=403)
            self.client.logout()

    def test_404_page(self):
        self.client.force_login(mk(Role.ADMINISTRATOR))
        r = self.client.get(reverse("ui:role-change", args=[9999]))
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "Page not found", status_code=404)


class UserListTests(TestCase):
    def test_admin_can_search_and_filter(self):
        self.client.force_login(mk(Role.ADMINISTRATOR))
        mk(Role.ORGANIZER, "olivia"); mk(Role.ATTENDEE, "arun")
        r = self.client.get(reverse("ui:users"), {"role": "organizer"})
        self.assertContains(r, "olivia"); self.assertNotContains(r, "arun")
        r = self.client.get(reverse("ui:users"), {"q": "zzz"})
        self.assertContains(r, "No users match")


class RoleChangeUITests(TestCase):
    def setUp(self):
        self.admin = mk(Role.ADMINISTRATOR)
        self.target = mk(Role.ATTENDEE, "target")
        self.client.force_login(self.admin)
        self.url = reverse("ui:role-change", args=[self.target.pk])

    def test_page_renders(self):
        self.assertContains(self.client.get(self.url), "Change role for target")

    def test_success_with_confirmation_and_reason(self):
        r = self.client.post(self.url, {"role": "organizer", "reason": "approved", "confirm": "1"})
        self.assertRedirects(r, reverse("ui:users"))
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.ORGANIZER)

    def test_requires_confirm_and_reason_and_shows_all_errors(self):
        r = self.client.post(self.url, {"role": "organizer", "reason": ""})
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "Tick the box", status_code=400)
        self.assertContains(r, "Enter a reason", status_code=400)
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.ATTENDEE)

    def test_non_admin_cannot_post(self):
        self.client.force_login(self.target)
        r = self.client.post(self.url, {"role": "administrator", "reason": "x", "confirm": "1"})
        self.assertEqual(r.status_code, 403)
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.ATTENDEE)
