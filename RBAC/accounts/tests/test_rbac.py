"""EMS-F-005 / Test Plan TC-03: permitted and denied access per role."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.decorators import role_required
from accounts.permissions import IsEventOwner
from accounts.roles import DEFAULT_ROLE, Role

User = get_user_model()

AREAS = {
    Role.ATTENDEE: "rbac:attendee-area",
    Role.ORGANIZER: "rbac:organizer-area",
    Role.ADMINISTRATOR: "rbac:admin-area",
}


def make_user(role, name=None):
    name = name or role
    return User.objects.create_user(username=name, email=f"{name}@x.com",
                                    password="pw12345!", role=role)


class RoleDistinctionTests(TestCase):
    def test_default_role_is_attendee(self):
        u = User.objects.create_user("new", "new@x.com", "pw12345!")
        self.assertEqual(u.role, DEFAULT_ROLE)
        self.assertEqual(u.role, Role.ATTENDEE)

    def test_three_roles_exist(self):
        self.assertEqual(set(Role.values), {"attendee", "organizer", "administrator"})


class AccessMatrixTests(TestCase):
    def test_each_role_only_reaches_its_own_area(self):
        for role in Role.values:
            user = make_user(role)
            client = APIClient()
            client.force_login(user)
            for area_role, url_name in AREAS.items():
                resp = client.get(reverse(url_name))
                expected = 200 if area_role == role else 403
                self.assertEqual(resp.status_code, expected,
                                 f"{role} -> {url_name}: got {resp.status_code}")

    def test_unauthenticated_gets_401(self):
        client = APIClient()
        for url_name in AREAS.values():
            self.assertEqual(client.get(reverse(url_name)).status_code, 401)


class RoleChangeTests(TestCase):
    def setUp(self):
        self.admin = make_user(Role.ADMINISTRATOR)
        self.target = make_user(Role.ATTENDEE, "target")
        self.url = reverse("rbac:change-role", args=[self.target.pk])

    def test_admin_can_change_role(self):
        c = APIClient(); c.force_login(self.admin)
        r = c.post(self.url, {"role": "organizer", "reason": "approved"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.ORGANIZER)

    def test_requires_reason_and_valid_role(self):
        c = APIClient(); c.force_login(self.admin)
        self.assertEqual(c.post(self.url, {"role": "organizer"}, format="json").status_code, 400)
        self.assertEqual(c.post(self.url, {"role": "god", "reason": "x"}, format="json").status_code, 400)

    def test_cannot_change_own_role(self):
        c = APIClient(); c.force_login(self.admin)
        url = reverse("rbac:change-role", args=[self.admin.pk])
        self.assertEqual(c.post(url, {"role": "attendee", "reason": "x"}, format="json").status_code, 400)

    def test_non_admin_cannot_escalate_self(self):
        c = APIClient(); c.force_login(self.target)
        url = reverse("rbac:change-role", args=[self.target.pk])
        r = c.post(url, {"role": "administrator", "reason": "pls"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.ATTENDEE)


class ObjectOwnershipTests(TestCase):
    class FakeEvent:
        def __init__(self, organizer_id): self.organizer_id = organizer_id
        @property
        def organizer(self): return self.organizer_id

    def test_only_owner_passes(self):
        owner = make_user(Role.ORGANIZER, "o1")
        other = make_user(Role.ORGANIZER, "o2")
        event = self.FakeEvent(owner.pk)
        perm = IsEventOwner()

        class Req:  # minimal stand-in
            def __init__(self, user): self.user = user

        self.assertTrue(perm.has_object_permission(Req(owner), object(), event))
        self.assertFalse(perm.has_object_permission(Req(other), object(), event))


class TemplateViewDecoratorTests(TestCase):
    def test_decorator_denies_wrong_role_with_403_page(self):
        from django.core.exceptions import PermissionDenied
        from django.test import RequestFactory

        @role_required(Role.ORGANIZER)
        def view(request): return "ok"

        rf = RequestFactory()
        req = rf.get("/x"); req.user = make_user(Role.ATTENDEE)
        with self.assertRaises(PermissionDenied):
            view(req)
        req.user = make_user(Role.ORGANIZER, "org")
        self.assertEqual(view(req), "ok")
