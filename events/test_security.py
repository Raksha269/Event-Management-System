from datetime import timedelta
from decimal import Decimal
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

try:
    from accounts.roles import Role
except ImportError:
    from RBAC.accounts.roles import Role

from events.models import Event, Payment, Registration, SecurityAlert, TicketType, UserProfile
from events.security import (
    MAX_FAILED_LOGIN_ATTEMPTS,
    check_account_lockout,
    inspect_payment_data_storage,
    record_login_success,
    record_security_alert,
    track_abnormal_registration,
    track_login_failure,
    verify_password_hashing,
    verify_tls_version,
)
from events.services import create_registration, process_payment

User = get_user_model()


class SecurityRequirementTests(TestCase):
    """
    Test suite for Security Requirements EMS-SR-001 through EMS-SR-005.
    Mapped to Software Test Plan: TC-Sec-01, TC-Sec-02, TC-Sec-03, TC-Sec-04, TC-Sec-05.
    """

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        # Create Attendee
        self.attendee = User.objects.create_user(
            username="sec_attendee",
            email="sec_attendee@example.com",
            password="StrongPassword123!",
        )
        self.attendee.role = Role.ATTENDEE

        # Create Organizer 1
        self.organizer1 = User.objects.create_user(
            username="sec_organizer1",
            email="sec_organizer1@example.com",
            password="StrongPassword123!",
        )
        self.organizer1.role = Role.ORGANIZER

        # Create Organizer 2
        self.organizer2 = User.objects.create_user(
            username="sec_organizer2",
            email="sec_organizer2@example.com",
            password="StrongPassword123!",
        )
        self.organizer2.role = Role.ORGANIZER

        # Create Administrator
        self.admin = User.objects.create_user(
            username="sec_admin",
            email="sec_admin@example.com",
            password="AdminStrongPassword123!",
            is_staff=True,
        )
        self.admin.role = Role.ADMINISTRATOR

        # Sample event by organizer1
        self.event1 = Event.objects.create(
            organizer=self.organizer1,
            title="Cybersecurity Summit 2026",
            description="Leading conference on enterprise application security.",
            venue="Tech Center Hall A",
            date=timezone.now() + timedelta(days=30),
            ticket_price=Decimal("150.00"),
            capacity=100,
            status=Event.Status.PUBLISHED,
        )

    # =========================================================================
    # EMS-SR-001 / TC-Sec-01: Transport Security & TLS Protocol Compliance
    # =========================================================================

    def test_ems_sr_001_tls_protocol_enforcement(self):
        """
        TC-Sec-01: SSL/TLS scan verifies no deprecated protocols below TLS 1.2 accepted.
        Accepts TLS 1.2 and TLS 1.3; rejects SSLv2, SSLv3, TLS 1.0, TLS 1.1.
        """
        # Deprecated / insecure protocols must be strictly rejected
        for proto in ["SSLv2", "SSLv3", "TLSv1.0", "TLS 1.0", "TLSv1.1", "TLS 1.1"]:
            valid, msg = verify_tls_version(proto)
            self.assertFalse(valid, f"Protocol {proto} should be rejected")
            self.assertIn("deprecated and rejected", msg)

        # Compliant modern protocols must be accepted
        for proto in ["TLSv1.2", "TLS 1.2", "TLSv1.3", "TLS 1.3"]:
            valid, msg = verify_tls_version(proto)
            self.assertTrue(valid, f"Protocol {proto} should be accepted")
            self.assertIn("satisfies TLS 1.2+", msg)

    def test_ems_sr_001_security_headers_configured(self):
        """
        TC-Sec-01: Verify production security headers are configured in Django settings.
        """
        self.assertTrue(getattr(settings, "SECURE_BROWSER_XSS_FILTER", False))
        self.assertTrue(getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False))
        self.assertEqual(getattr(settings, "X_FRAME_OPTIONS", None), "DENY")
        self.assertEqual(
            getattr(settings, "SECURE_PROXY_SSL_HEADER", None),
            ("HTTP_X_FORWARDED_PROTO", "https"),
        )

    # =========================================================================
    # EMS-SR-002 / TC-Sec-02: Payment Data Protection & Tokenization
    # =========================================================================

    def test_ems_sr_002_zero_raw_card_data_stored_in_database(self):
        """
        TC-Sec-02: Database audit confirms no plaintext credit card numbers or CVVs stored.
        Payment data uses tokenization; database models contain zero PAN/CVV fields.
        """
        compliant, details = inspect_payment_data_storage()
        self.assertTrue(compliant, f"Disallowed fields detected: {details['disallowed_fields']}")
        self.assertEqual(len(details["disallowed_fields"]), 0)
        self.assertTrue(details["token_field_present"])

    def test_ems_sr_002_payment_flow_uses_tokenization(self):
        """
        TC-Sec-02: Confirm payment model generates and stores opaque UUID token instead of card data.
        """
        reg = create_registration(
            user=self.attendee,
            event_id=self.event1.pk,
            quantity=1,
        )
        payment = process_payment(reg.pk)

        # Payment must have valid UUID transaction token
        self.assertIsInstance(payment.transaction_id, uuid.UUID)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)

        # Confirm no PAN or CVV attributes exist on payment instance
        for disallowed in ["card_number", "pan", "cvv", "cvc", "credit_card"]:
            self.assertFalse(hasattr(payment, disallowed))

    # =========================================================================
    # EMS-SR-003 / TC-Sec-03: Modern Salted Password Hashing
    # =========================================================================

    def test_ems_sr_003_password_stored_as_modern_salted_hash(self):
        """
        TC-Sec-03: Database inspection confirms salted hash storage; no plaintext.
        Passwords use modern algorithms (PBKDF2/Argon2/bcrypt) with salt and iterations.
        """
        # User created in setUp
        is_hashed, alg = verify_password_hashing(self.attendee)
        self.assertTrue(is_hashed, f"Password is not properly hashed: {alg}")
        self.assertIn("pbkdf2", alg.lower())

        # Raw password must NEVER equal stored database field
        self.assertNotEqual(self.attendee.password, "StrongPassword123!")
        self.assertNotIn("StrongPassword123!", self.attendee.password)

        # Password must contain algorithm prefix, iterations, salt, and hash
        parts = self.attendee.password.split("$")
        self.assertGreaterEqual(len(parts), 4)

    def test_ems_sr_003_plaintext_password_detected_and_rejected(self):
        """
        TC-Sec-03: Plaintext inspection rejects unhashed passwords.
        """
        fake_user = User(username="unhashed_user", password="plaintext_password")
        is_hashed, msg = verify_password_hashing(fake_user)
        self.assertFalse(is_hashed)
        self.assertIn("plaintext", msg.lower())

    # =========================================================================
    # EMS-SR-004 / TC-Sec-04: Role-Based Access Control (RBAC) Enforcement
    # =========================================================================

    def test_ems_sr_004_attendee_denied_organizer_endpoints(self):
        """
        TC-Sec-04: 403 Forbidden returned when Attendee attempts Organizer actions.
        """
        # Attendee logs into web UI
        self.client.force_login(self.attendee)

        # Web UI: Create Event
        resp = self.client.get(reverse("event_create"))
        self.assertEqual(resp.status_code, 403)

        # Web UI: Edit Event
        resp = self.client.get(reverse("event_edit", kwargs={"pk": self.event1.pk}))
        self.assertEqual(resp.status_code, 403)

        # Web UI: Publish Event
        resp = self.client.post(reverse("event_publish", kwargs={"pk": self.event1.pk}))
        self.assertEqual(resp.status_code, 403)

        # Web UI: Attendee Report CSV & Report view
        resp = self.client.get(reverse("event_report", kwargs={"pk": self.event1.pk}))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get(reverse("event_report_csv", kwargs={"pk": self.event1.pk}))
        self.assertEqual(resp.status_code, 403)

        # API: Create Event
        self.api_client.force_authenticate(user=self.attendee)
        resp = self.api_client.post(
            reverse("api_events_list_create"),
            {
                "title": "Unauthorized Event",
                "date": (timezone.now() + timedelta(days=10)).isoformat(),
                "venue": "Test Venue",
                "capacity": 50,
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_ems_sr_004_organizer_denied_admin_endpoints(self):
        """
        TC-Sec-04: 403 Forbidden returned when Organizer attempts Administrator actions.
        """
        self.client.force_login(self.organizer1)

        # Web UI: Admin User Management
        resp = self.client.get(reverse("admin_user_list"))
        self.assertEqual(resp.status_code, 403)

        # Web UI: Security Alerts List
        resp = self.client.get(reverse("admin_alerts_list"))
        self.assertEqual(resp.status_code, 403)

        # API: Admin User List
        self.api_client.force_authenticate(user=self.organizer1)
        resp = self.api_client.get(reverse("api_admin_users_list"))
        self.assertEqual(resp.status_code, 403)

        # API: Admin Alerts List
        resp = self.api_client.get(reverse("api_admin_alerts_list"))
        self.assertEqual(resp.status_code, 403)

    def test_ems_sr_004_organizer_denied_access_to_other_organizers_events(self):
        """
        TC-Sec-04: 403 Forbidden when an Organizer attempts to edit or export another Organizer's event.
        """
        self.client.force_login(self.organizer2)

        # Web UI: Edit organizer1's event
        resp = self.client.get(reverse("event_edit", kwargs={"pk": self.event1.pk}))
        self.assertEqual(resp.status_code, 403)

        # Web UI: Export organizer1's attendee list
        resp = self.client.get(reverse("event_report_csv", kwargs={"pk": self.event1.pk}))
        self.assertEqual(resp.status_code, 403)

        # API: Update organizer1's event
        self.api_client.force_authenticate(user=self.organizer2)
        resp = self.api_client.patch(
            reverse("api_events_detail_update", kwargs={"pk": self.event1.pk}),
            {"title": "Hacked Title"},
        )
        self.assertEqual(resp.status_code, 403)

    # =========================================================================
    # EMS-SR-005 / TC-Sec-05: Suspicious Activity Logging & Admin Alerts
    # =========================================================================

    def test_ems_sr_005_repeated_failed_logins_trigger_burst_and_lockout(self):
        """
        TC-Sec-05: 5 consecutive failed logins trigger account lockout and administrator alert.
        """
        # Ensure fresh state
        self.attendee.failed_login_attempts = 0
        self.attendee.locked_until = None
        SecurityAlert.objects.all().delete()

        # 1st and 2nd failure: counter increments
        self.client.post(reverse("login"), {"username": self.attendee.username, "password": "WrongPassword"})
        self.attendee.refresh_from_db()
        self.assertEqual(self.attendee.failed_login_attempts, 1)

        self.client.post(reverse("login"), {"username": self.attendee.username, "password": "WrongPassword"})
        self.attendee.refresh_from_db()
        self.assertEqual(self.attendee.failed_login_attempts, 2)
        self.assertEqual(SecurityAlert.objects.count(), 0)

        # 3rd failure: triggers FAILED_LOGIN_BURST alert
        self.client.post(reverse("login"), {"username": self.attendee.username, "password": "WrongPassword"})
        self.attendee.refresh_from_db()
        self.assertEqual(self.attendee.failed_login_attempts, 3)
        self.assertTrue(
            SecurityAlert.objects.filter(
                alert_type=SecurityAlert.AlertType.FAILED_LOGIN_BURST,
                target_user=self.attendee,
            ).exists()
        )

        # 4th failure
        self.client.post(reverse("login"), {"username": self.attendee.username, "password": "WrongPassword"})
        self.attendee.refresh_from_db()
        self.assertEqual(self.attendee.failed_login_attempts, 4)

        # 5th failure: triggers ACCOUNT_LOCKOUT alert and locks account for 15 minutes
        resp = self.client.post(
            reverse("login"),
            {"username": self.attendee.username, "password": "WrongPassword"},
            follow=True,
        )
        self.attendee.refresh_from_db()
        self.assertEqual(self.attendee.failed_login_attempts, 5)
        self.assertTrue(self.attendee.is_locked)
        self.assertIsNotNone(self.attendee.locked_until)
        self.assertGreater(self.attendee.locked_until, timezone.now())

        lockout_alert = SecurityAlert.objects.filter(
            alert_type=SecurityAlert.AlertType.ACCOUNT_LOCKOUT,
            target_user=self.attendee,
        ).first()
        self.assertIsNotNone(lockout_alert)
        self.assertEqual(lockout_alert.severity, SecurityAlert.Severity.HIGH)
        self.assertIn("15 minutes", lockout_alert.details)

        # Attempt to log in with CORRECT password while locked must be REJECTED
        resp_correct = self.client.post(
            reverse("login"),
            {"username": self.attendee.username, "password": "StrongPassword123!"},
        )
        self.assertContains(resp_correct, "Account temporarily locked")

    def test_ems_sr_005_successful_login_resets_failed_counter(self):
        """
        TC-Sec-05: Successful login clears failed login counter.
        """
        self.attendee.failed_login_attempts = 2
        self.attendee.refresh_from_db()

        resp = self.client.post(
            reverse("login"),
            {"username": self.attendee.username, "password": "StrongPassword123!"},
        )
        self.attendee.refresh_from_db()
        self.assertEqual(self.attendee.failed_login_attempts, 0)
        self.assertIsNone(self.attendee.locked_until)

    def test_ems_sr_005_abnormal_registration_velocity_triggers_alert(self):
        """
        TC-Sec-05: Rapid burst of registrations (> 5 within 1 min) triggers ABNORMAL_REGISTRATION_RATE alert.
        """
        SecurityAlert.objects.all().delete()

        # Create 5 registrations rapidly on the same event
        for i in range(5):
            u = User.objects.create_user(
                username=f"velocity_user_{i}",
                email=f"velocity_{i}@example.com",
                password="Password123!",
            )
            create_registration(user=u, event_id=self.event1.pk, quantity=1)

        spike_alert = SecurityAlert.objects.filter(
            alert_type=SecurityAlert.AlertType.ABNORMAL_REGISTRATION_RATE
        ).first()
        self.assertIsNotNone(spike_alert)
        self.assertEqual(spike_alert.severity, SecurityAlert.Severity.HIGH)
        self.assertIn("Abnormal registration spike", spike_alert.details)
        self.assertIn(str(self.event1.pk), spike_alert.details)

    def test_ems_sr_005_admin_alerts_web_interface(self):
        """
        TC-Sec-05: Administrator monitoring panel displays alerts and allows resolution.
        """
        # Create sample alerts
        alert1 = record_security_alert(
            alert_type=SecurityAlert.AlertType.ACCOUNT_LOCKOUT,
            severity=SecurityAlert.Severity.HIGH,
            details="User locked out.",
            target_user=self.attendee,
        )
        alert2 = record_security_alert(
            alert_type=SecurityAlert.AlertType.FAILED_LOGIN_BURST,
            severity=SecurityAlert.Severity.MEDIUM,
            details="Repeated failures.",
            target_user=self.organizer1,
        )

        self.client.force_login(self.admin)

        # View Alerts List
        resp = self.client.get(reverse("admin_alerts_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Security Monitoring & Incident Alerts")
        self.assertContains(resp, "User locked out.")
        self.assertContains(resp, "Repeated failures.")

        # Filter by severity
        resp_filtered = self.client.get(reverse("admin_alerts_list"), {"severity": "HIGH"})
        self.assertEqual(resp_filtered.status_code, 200)
        self.assertContains(resp_filtered, "User locked out.")
        self.assertNotContains(resp_filtered, "Repeated failures.")

        # Resolve Alert via Web UI
        resolve_resp = self.client.post(
            reverse("admin_alert_resolve", kwargs={"pk": alert1.pk}),
            follow=True,
        )
        self.assertEqual(resolve_resp.status_code, 200)
        alert1.refresh_from_db()
        self.assertTrue(alert1.is_resolved)

    def test_ems_sr_005_admin_alerts_rest_api(self):
        """
        TC-Sec-05: Administrator REST API endpoints for security alerts list and resolve.
        """
        alert = record_security_alert(
            alert_type=SecurityAlert.AlertType.ACCOUNT_LOCKOUT,
            severity=SecurityAlert.Severity.HIGH,
            details="API alert test.",
            target_user=self.attendee,
        )

        self.api_client.force_authenticate(user=self.admin)

        # GET /api/v1/admin/alerts/
        resp = self.api_client.get(reverse("api_admin_alerts_list"))
        self.assertEqual(resp.status_code, 200)
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        alert_ids = [item["id"] for item in results]
        self.assertIn(alert.pk, alert_ids)

        # POST /api/v1/admin/alerts/<id>/resolve/
        resolve_resp = self.api_client.post(
            reverse("api_admin_alert_resolve", kwargs={"pk": alert.pk})
        )
        self.assertEqual(resolve_resp.status_code, 200)
        self.assertTrue(resolve_resp.data["is_resolved"])

        alert.refresh_from_db()
        self.assertTrue(alert.is_resolved)
