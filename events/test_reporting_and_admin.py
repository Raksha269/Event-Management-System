import csv
from datetime import timedelta
from decimal import Decimal
import io

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

try:
    from accounts.roles import Role
except ImportError:
    from RBAC.accounts.roles import Role

from .models import Event, Payment, Registration, TicketType, UserProfile
from .reports import generate_event_attendees_csv, get_event_report_data
from .services import create_registration, process_payment, process_refund


class ReportingTests(TestCase):
    """
    EMS-F-050: Reporting and CSV export tests (TC-Rep-01 / TC-09).
    """

    def setUp(self):
        # Organizer
        self.organizer = User.objects.create_user(
            username="rep_organizer",
            email="rep_org@gather.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.organizer,
            role=Role.ORGANIZER,
            email_verified=True,
        )

        # Other Organizer
        self.other_organizer = User.objects.create_user(
            username="other_organizer",
            email="other_org@gather.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.other_organizer,
            role=Role.ORGANIZER,
            email_verified=True,
        )

        # Regular Attendee
        self.attendee = User.objects.create_user(
            username="rep_attendee",
            email="attendee@gather.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.attendee,
            role=Role.ATTENDEE,
            email_verified=True,
        )

        # Second Attendee
        self.attendee2 = User.objects.create_user(
            username="rep_attendee2",
            email="attendee2@gather.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.attendee2,
            role=Role.ATTENDEE,
            email_verified=True,
        )

        # Administrator
        self.admin_user = User.objects.create_user(
            username="rep_admin",
            email="admin@gather.test",
            password="StrongPass123!",
            is_staff=True,
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=Role.ADMINISTRATOR,
            email_verified=True,
        )

        # Event
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Developer Summit 2026",
            title="Developer Summit 2026",
            description="Annual software developers convention.",
            category="Technology",
            venue="Grand Arena",
            date=timezone.now() + timedelta(days=20),
            ticket_price=Decimal("1000.00"),
            capacity=100,
            status=Event.Status.PUBLISHED,
        )

        # Ticket Types
        self.vip_tier = TicketType.objects.create(
            event=self.event,
            name="VIP Pass",
            price=Decimal("2500.00"),
            quantity_limit=20,
        )
        self.regular_tier = TicketType.objects.create(
            event=self.event,
            name="Regular Pass",
            price=Decimal("1000.00"),
            quantity_limit=80,
        )

        # Registrations:
        # 1. Confirmed & Paid VIP ticket
        self.reg1 = create_registration(
            user=self.attendee,
            event_id=self.event.pk,
            ticket_type_id=self.vip_tier.pk,
            quantity=1,
        )
        self.payment1 = process_payment(self.reg1.pk)

        # 2. Confirmed & Paid Regular ticket
        self.reg2 = create_registration(
            user=self.attendee2,
            event_id=self.event.pk,
            ticket_type_id=self.regular_tier.pk,
            quantity=2,
        )
        self.payment2 = process_payment(self.reg2.pk)

    def test_report_service_calculates_accurate_metrics(self):
        """EMS-F-050: Service accurately aggregates revenue and attendee metrics."""
        report = get_event_report_data(self.event)

        # 1 VIP (₹2500) + 2 Regular (2 x ₹1000 = ₹2000) = ₹4500 Gross
        self.assertEqual(report["gross_revenue"], Decimal("4500.00"))
        self.assertEqual(report["total_refunded"], Decimal("0.00"))
        self.assertEqual(report["net_revenue"], Decimal("4500.00"))
        self.assertEqual(report["confirmed_tickets_count"], 3)
        self.assertEqual(report["total_registrations_count"], 2)

        # Check attendee list
        usernames = [r["username"] for r in report["attendee_records"]]
        self.assertIn("rep_attendee", usernames)
        self.assertIn("rep_attendee2", usernames)

    def test_report_reflects_refunds_in_net_revenue(self):
        """EMS-F-050: Completed refunds reduce net revenue and update payment status."""
        process_refund(self.payment1.pk, "Requested cancellation")

        report = get_event_report_data(self.event)
        self.assertEqual(report["gross_revenue"], Decimal("4500.00"))
        self.assertEqual(report["total_refunded"], Decimal("2500.00"))
        self.assertEqual(report["net_revenue"], Decimal("2000.00"))

    def test_organizer_can_view_event_report_dashboard(self):
        """EMS-F-050: Owning organizer can access on-screen attendee and revenue report."""
        self.client.force_login(self.organizer)
        response = self.client.get(
            reverse("event_report", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendee & Revenue Report")
        self.assertContains(response, "Developer Summit 2026")
        self.assertContains(response, "4500.00")
        self.assertContains(response, "rep_attendee")
        self.assertContains(response, "rep_attendee2")

    def test_csv_export_matches_database_and_onscreen_data(self):
        """
        AC-EMS-F-050: Exported CSV matches on-screen attendee and revenue data (TC-Rep-01).
        """
        self.client.force_login(self.organizer)
        response = self.client.get(
            reverse("event_report_csv", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            f'filename="event_{self.event.pk}_attendees.csv"',
            response["Content-Disposition"],
        )

        content = response.content.decode("utf-8")
        reader = list(csv.reader(io.StringIO(content)))

        # Find rows
        rows_dict = {row[0]: row[1:] for row in reader if row}
        self.assertIn("Gross Revenue", rows_dict)
        self.assertEqual(rows_dict["Gross Revenue"][0], "4500.00")
        self.assertEqual(rows_dict["Net Revenue"][0], "4500.00")
        self.assertEqual(rows_dict["Confirmed Attendees"][0], "3")

        # Find attendee rows
        csv_text = response.content.decode("utf-8")
        self.assertIn("rep_attendee", csv_text)
        self.assertIn("rep_attendee2", csv_text)
        self.assertIn("VIP Pass", csv_text)
        self.assertIn("Regular Pass", csv_text)

    def test_api_csv_report_endpoint(self):
        """GET /api/v1/events/{id}/reports/attendees.csv - Owning organizer."""
        self.client.force_login(self.organizer)
        response = self.client.get(
            reverse("api_event_report_csv", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Developer Summit 2026", response.content.decode("utf-8"))

    def test_unauthorized_organizer_cannot_view_or_export_report(self):
        """EMS-F-050: Organizers cannot view reports for events they do not own (403)."""
        self.client.force_login(self.other_organizer)

        # Web view
        web_response = self.client.get(
            reverse("event_report", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(web_response.status_code, 403)

        # CSV view
        csv_response = self.client.get(
            reverse("event_report_csv", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(csv_response.status_code, 403)

        # API view
        api_response = self.client.get(
            reverse("api_event_report_csv", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(api_response.status_code, 403)

    def test_attendee_cannot_access_event_report(self):
        """EMS-F-050: Attendees are forbidden from accessing event reports (403)."""
        self.client.force_login(self.attendee)

        web_response = self.client.get(
            reverse("event_report", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(web_response.status_code, 403)

        api_response = self.client.get(
            reverse("api_event_report_csv", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(api_response.status_code, 403)

    def test_administrator_can_view_and_export_any_event_report(self):
        """EMS-F-050: Administrators have system-wide reporting permissions."""
        self.client.force_login(self.admin_user)

        web_res = self.client.get(
            reverse("event_report", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(web_res.status_code, 200)

        csv_res = self.client.get(
            reverse("api_event_report_csv", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(csv_res.status_code, 200)


class UserAdministrationTests(TestCase):
    """
    EMS-F-051: User / Account Administration tests (TC-Adm-01 / TC-03).
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username="sys_admin",
            email="sys_admin@gather.test",
            password="StrongAdminPass!99",
            is_staff=True,
        )
        UserProfile.objects.create(
            user=self.admin,
            role=Role.ADMINISTRATOR,
            email_verified=True,
        )

        self.organizer = User.objects.create_user(
            username="regular_org",
            email="org@gather.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.organizer,
            role=Role.ORGANIZER,
            email_verified=True,
        )

        self.target_user = User.objects.create_user(
            username="target_member",
            email="target@gather.test",
            password="StrongTargetPass!123",
            is_active=True,
        )
        UserProfile.objects.create(
            user=self.target_user,
            role=Role.ATTENDEE,
            email_verified=True,
        )

    def test_administrator_can_view_user_list(self):
        """EMS-F-051: Administrator can access user management dashboard."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User Account Administration")
        self.assertContains(response, "target_member")
        self.assertContains(response, "regular_org")

    def test_non_administrator_cannot_access_user_management(self):
        """EMS-F-051 / TC-03: Attendees and Organizers get 403 on admin views."""
        # Organizer forbidden
        self.client.force_login(self.organizer)
        org_res = self.client.get(reverse("admin_user_list"))
        self.assertEqual(org_res.status_code, 403)

        # Attendee forbidden
        self.client.force_login(self.target_user)
        att_res = self.client.get(reverse("admin_user_list"))
        self.assertEqual(att_res.status_code, 403)

    def test_administrator_can_deactivate_and_reactivate_user(self):
        """
        AC-EMS-F-051: Deactivated accounts cannot log in; reactivation restores access.
        """
        self.client.force_login(self.admin)

        # 1. Deactivate target user
        toggle_res = self.client.post(
            reverse("admin_user_toggle_active", kwargs={"pk": self.target_user.pk})
        )
        self.assertEqual(toggle_res.status_code, 302)

        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)

        # 2. Verify deactivated account CANNOT log in (AC-EMS-F-051)
        self.client.logout()
        login_res = self.client.post(
            reverse("login"),
            {
                "username": "target_member",
                "password": "StrongTargetPass!123",
            },
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertFalse(login_res.wsgi_request.user.is_authenticated)

        # 3. Reactivate target user
        self.client.force_login(self.admin)
        reactivate_res = self.client.post(
            reverse("admin_user_toggle_active", kwargs={"pk": self.target_user.pk})
        )
        self.assertEqual(reactivate_res.status_code, 302)

        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)

        # 4. Verify reactivated user CAN now log in
        self.client.logout()
        login_res2 = self.client.post(
            reverse("login"),
            {
                "username": "target_member",
                "password": "StrongTargetPass!123",
            },
        )
        self.assertEqual(login_res2.status_code, 302)
        self.assertTrue(login_res2.wsgi_request.user.is_authenticated)

    def test_administrator_cannot_deactivate_own_account(self):
        """EMS-F-051: Safety check prevents admin self-lockout."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin_user_toggle_active", kwargs={"pk": self.admin.pk})
        )
        self.assertEqual(response.status_code, 302)

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_administrator_can_change_user_role_takes_immediate_effect(self):
        """
        AC-EMS-F-051: Role changes take effect immediately on permissions.
        """
        self.client.force_login(self.admin)

        # Promote target_user from attendee to organizer
        change_res = self.client.post(
            reverse("admin_user_change_role", kwargs={"pk": self.target_user.pk}),
            {"role": Role.ORGANIZER},
        )
        self.assertEqual(change_res.status_code, 302)

        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.role, Role.ORGANIZER)
        self.assertTrue(self.target_user.is_organizer)

        # Test that newly promoted organizer can immediately access organizer endpoints
        self.client.force_login(self.target_user)
        event_create_res = self.client.get(reverse("event_create"))
        self.assertEqual(event_create_res.status_code, 200)

        # Now demote back to attendee
        self.client.force_login(self.admin)
        demote_res = self.client.post(
            reverse("admin_user_change_role", kwargs={"pk": self.target_user.pk}),
            {"role": Role.ATTENDEE},
        )
        self.assertEqual(demote_res.status_code, 302)

        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.role, Role.ATTENDEE)

        # Verify immediate revocation of organizer access
        self.client.force_login(self.target_user)
        denied_res = self.client.get(reverse("event_create"))
        self.assertEqual(denied_res.status_code, 403)

    def test_administrator_cannot_change_own_role(self):
        """EMS-F-051: Safety check prevents admin from removing their own admin role."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin_user_change_role", kwargs={"pk": self.admin.pk}),
            {"role": Role.ATTENDEE},
        )
        self.assertEqual(response.status_code, 302)

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, Role.ADMINISTRATOR)

    # --- REST API Endpoints (SAD 4.3 Specification) ---

    def test_api_admin_users_list(self):
        """GET /api/v1/admin/users/ - Administrator retrieves user list."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("api_admin_users_list"))
        self.assertEqual(response.status_code, 200)
        usernames = [u["username"] for u in response.data]
        self.assertIn("sys_admin", usernames)
        self.assertIn("target_member", usernames)

    def test_api_admin_users_list_forbidden_for_non_admin(self):
        """GET /api/v1/admin/users/ - Returns 403 for non-admin."""
        self.client.force_login(self.organizer)
        response = self.client.get(reverse("api_admin_users_list"))
        self.assertEqual(response.status_code, 403)

    def test_api_admin_patch_user_role_and_active_status(self):
        """PATCH /api/v1/admin/users/{id}/ - Administrator updates role and active flag."""
        self.client.force_login(self.admin)
        response = self.client.patch(
            reverse(
                "api_admin_users_detail_update",
                kwargs={"pk": self.target_user.pk},
            ),
            {"role": "organizer", "is_active": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "organizer")
        self.assertFalse(response.data["is_active"])

        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.role, Role.ORGANIZER)
        self.assertFalse(self.target_user.is_active)

    def test_api_admin_patch_self_deactivation_rejected(self):
        """PATCH /api/v1/admin/users/{id}/ - Self deactivation rejected (400)."""
        self.client.force_login(self.admin)
        response = self.client.patch(
            reverse(
                "api_admin_users_detail_update",
                kwargs={"pk": self.admin.pk},
            ),
            {"is_active": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "CANNOT_DEACTIVATE_SELF")

    def test_api_admin_patch_self_role_change_rejected(self):
        """PATCH /api/v1/admin/users/{id}/ - Self role change rejected (400)."""
        self.client.force_login(self.admin)
        response = self.client.patch(
            reverse(
                "api_admin_users_detail_update",
                kwargs={"pk": self.admin.pk},
            ),
            {"role": "attendee"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "CANNOT_CHANGE_OWN_ROLE")
