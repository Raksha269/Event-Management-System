import concurrent.futures
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

try:
    from accounts.roles import Role
except ImportError:
    from RBAC.accounts.roles import Role

from .models import Event, Registration, TicketType, UserProfile
from .services import create_registration, process_payment, process_refund


class EventManagementTests(TestCase):
    def setUp(self):
        # Create organizer user
        self.organizer = User.objects.create_user(
            username="organizer_alice",
            email="alice@gather.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.organizer,
            role=Role.ORGANIZER,
            email_verified=True,
        )

        # Create second organizer
        self.other_organizer = User.objects.create_user(
            username="organizer_bob",
            email="bob@gather.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.other_organizer,
            role=Role.ORGANIZER,
            email_verified=True,
        )

        # Create regular attendee
        self.attendee = User.objects.create_user(
            username="attendee_charlie",
            email="charlie@gather.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.attendee,
            role=Role.ATTENDEE,
            email_verified=True,
        )

        # Sample event
        self.future_date = timezone.now() + timedelta(days=14)
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Cloud Native Summit",
            title="Cloud Native Summit",
            description="Summit on cloud native architecture and containers.",
            category="Technology",
            venue="Tech Convention Hall",
            date=self.future_date,
            ticket_price=Decimal("1500.00"),
            capacity=50,
            status=Event.Status.DRAFT,
        )

    # --- EMS-F-010: Event Creation & Dashboard Tests (TC-Evt-01 / TC-04) ---

    def test_organizer_can_create_event_saved_as_draft(self):
        """EMS-F-010: Authorized organizer creates event, saved as Draft, appears on dashboard."""
        self.client.force_login(self.organizer)

        event_date = timezone.now() + timedelta(days=30)
        response = self.client.post(
            reverse("event_create"),
            {
                "title": "AI and Robotics Workshop",
                "description": "Hands-on machine learning and robotics.",
                "category": "Workshop",
                "venue": "Lab 4, Innovation Campus",
                "date": event_date.strftime("%Y-%m-%dT%H:%M"),
                "capacity": 30,
                "ticket_price": "250.00",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("organizer_dashboard"))

        new_event = Event.objects.get(title="AI and Robotics Workshop")
        self.assertEqual(new_event.organizer, self.organizer)
        self.assertEqual(new_event.status, Event.Status.DRAFT)
        self.assertEqual(new_event.capacity, 30)
        self.assertEqual(new_event.ticket_price, Decimal("250.00"))

        # Verify it appears in organizer dashboard
        dashboard_response = self.client.get(reverse("organizer_dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "AI and Robotics Workshop")
        self.assertContains(dashboard_response, "Draft")

    def test_attendee_cannot_create_event(self):
        """EMS-F-010 / EMS-F-005: Non-organizer (attendee) receives 403 Forbidden on event create."""
        self.client.force_login(self.attendee)
        response = self.client.get(reverse("event_create"))
        self.assertEqual(response.status_code, 403)

        post_response = self.client.post(
            reverse("event_create"),
            {
                "title": "Unauthorized Event",
                "category": "General",
                "venue": "Nowhere",
                "date": (timezone.now() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M"),
                "capacity": 10,
                "ticket_price": "0.00",
            },
        )
        self.assertEqual(post_response.status_code, 403)
        self.assertFalse(Event.objects.filter(title="Unauthorized Event").exists())

    def test_event_creation_validates_capacity_and_price(self):
        """EMS-F-010: Capacity must be > 0 and ticket price >= 0."""
        self.client.force_login(self.organizer)
        response = self.client.post(
            reverse("event_create"),
            {
                "title": "Invalid Capacity Event",
                "category": "Test",
                "venue": "Test Venue",
                "date": (timezone.now() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M"),
                "capacity": 0,
                "ticket_price": "-10.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "capacity", "Capacity must be greater than zero."
        )
        self.assertFormError(
            response.context["form"], "ticket_price", "Ticket price cannot be negative."
        )

    # --- EMS-F-011: Event Editing Tests (TC-Evt-02) ---

    def test_organizer_can_edit_event_prior_to_start_date(self):
        """EMS-F-011: Changes persist and reflect when edited before start date."""
        self.client.force_login(self.organizer)

        edit_response = self.client.post(
            reverse("event_edit", kwargs={"pk": self.event.pk}),
            {
                "title": "Cloud Native Summit 2026 - Updated",
                "description": "Updated agenda with keynote speakers.",
                "category": "Technology",
                "venue": "Grand Ballroom, Tech Center",
                "date": (self.event.date + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "capacity": 75,
                "ticket_price": "2000.00",
            },
        )
        self.assertEqual(edit_response.status_code, 302)

        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Cloud Native Summit 2026 - Updated")
        self.assertEqual(self.event.venue, "Grand Ballroom, Tech Center")
        self.assertEqual(self.event.capacity, 75)
        self.assertEqual(self.event.ticket_price, Decimal("2000.00"))

    def test_editing_after_start_date_is_blocked(self):
        """EMS-F-011: Editing is rejected if the event has already started."""
        # Set date in the past
        past_event = Event.objects.create(
            organizer=self.organizer,
            name="Past Conference",
            title="Past Conference",
            venue="Old Hall",
            date=timezone.now() - timedelta(days=2),
            ticket_price=Decimal("100.00"),
            capacity=50,
            status=Event.Status.PUBLISHED,
        )

        self.client.force_login(self.organizer)
        response = self.client.post(
            reverse("event_edit", kwargs={"pk": past_event.pk}),
            {
                "title": "Past Conference Changed",
                "category": "General",
                "venue": "New Hall",
                "date": timezone.now().strftime("%Y-%m-%dT%H:%M"),
                "capacity": 50,
                "ticket_price": "100.00",
            },
        )
        self.assertEqual(response.status_code, 400)
        past_event.refresh_from_db()
        self.assertEqual(past_event.title, "Past Conference")

    def test_organizer_cannot_edit_another_organizers_event(self):
        """EMS-F-011 / IsEventOwner: Bob cannot edit Alice's event -> 403 Forbidden."""
        self.client.force_login(self.other_organizer)
        response = self.client.get(
            reverse("event_edit", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(response.status_code, 403)

        post_response = self.client.post(
            reverse("event_edit", kwargs={"pk": self.event.pk}),
            {
                "title": "Hacked Title",
                "venue": "Hacked Venue",
                "date": self.future_date.strftime("%Y-%m-%dT%H:%M"),
                "capacity": 50,
                "ticket_price": "0.00",
            },
        )
        self.assertEqual(post_response.status_code, 403)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Cloud Native Summit")

    # --- EMS-F-012: Publication & Public Visibility Tests (TC-Evt-03) ---

    def test_unpublished_events_hidden_from_public_search(self):
        """EMS-F-012: Unpublished/Draft events do not appear in public discover/search."""
        self.assertEqual(self.event.status, Event.Status.DRAFT)

        response = self.client.get(reverse("discover_events"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Cloud Native Summit")

        # Detail view should return 404 for unauthenticated or non-owner attendee
        self.client.force_login(self.attendee)
        detail_response = self.client.get(
            reverse("event_detail", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(detail_response.status_code, 404)

    def test_publishing_makes_event_visible_to_public(self):
        """EMS-F-012: Owning organizer publishes event -> appears in search and detail."""
        self.client.force_login(self.organizer)

        publish_response = self.client.post(
            reverse("event_publish", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(publish_response.status_code, 302)

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.PUBLISHED)
        self.assertTrue(self.event.is_published)

        # Now public can see it in discover
        self.client.logout()
        discover_response = self.client.get(reverse("discover_events"))
        self.assertEqual(discover_response.status_code, 200)
        self.assertContains(discover_response, "Cloud Native Summit")

        # Public can view detail page
        detail_response = self.client.get(
            reverse("event_detail", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Cloud Native Summit")

    def test_unpublishing_removes_event_from_public_visibility(self):
        """EMS-F-012: Unpublishing immediately hides event from public browse."""
        self.event.status = Event.Status.PUBLISHED
        self.event.save()

        self.client.force_login(self.organizer)
        unpublish_response = self.client.post(
            reverse("event_unpublish", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(unpublish_response.status_code, 302)

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.UNPUBLISHED)

        # Public search no longer shows it
        self.client.logout()
        discover_response = self.client.get(reverse("discover_events"))
        self.assertNotContains(discover_response, "Cloud Native Summit")

    # --- EMS-F-013: Ticket Types Configuration Tests (TC-Evt-04) ---

    def test_organizer_can_configure_ticket_types(self):
        """EMS-F-013: Organizer defines ticket types with name, price, and quantity limit."""
        self.client.force_login(self.organizer)

        # Add Early Bird ticket tier
        response = self.client.post(
            reverse("ticket_types_manage", kwargs={"pk": self.event.pk}),
            {
                "name": "Early Bird",
                "price": "999.00",
                "quantity_limit": 20,
            },
        )
        self.assertEqual(response.status_code, 302)

        # Add VIP ticket tier
        response2 = self.client.post(
            reverse("ticket_types_manage", kwargs={"pk": self.event.pk}),
            {
                "name": "VIP Pass",
                "price": "2999.00",
                "quantity_limit": 10,
            },
        )
        self.assertEqual(response2.status_code, 302)

        self.assertEqual(self.event.ticket_types.count(), 2)
        early_bird = self.event.ticket_types.get(name="Early Bird")
        self.assertEqual(early_bird.price, Decimal("999.00"))
        self.assertEqual(early_bird.quantity_limit, 20)
        self.assertEqual(early_bird.available_quantity, 20)
        self.assertFalse(early_bird.is_sold_out)

    def test_ticket_types_cannot_exceed_event_capacity(self):
        """EMS-F-013: Sum of ticket tier allocations cannot exceed event capacity."""
        self.client.force_login(self.organizer)

        # self.event has capacity = 50
        response = self.client.post(
            reverse("ticket_types_manage", kwargs={"pk": self.event.pk}),
            {
                "name": "Overallocated Pass",
                "price": "500.00",
                "quantity_limit": 60,  # Exceeds 50
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "quantity_limit",
            "Total ticket quantity (60) cannot exceed event capacity (50).",
        )
        self.assertEqual(self.event.ticket_types.count(), 0)

    def test_ticket_type_name_must_be_unique_per_event(self):
        """EMS-F-013: Duplicate ticket tier names on same event are rejected."""
        TicketType.objects.create(
            event=self.event,
            name="General",
            price=Decimal("500.00"),
            quantity_limit=25,
        )

        self.client.force_login(self.organizer)
        response = self.client.post(
            reverse("ticket_types_manage", kwargs={"pk": self.event.pk}),
            {
                "name": "General",
                "price": "600.00",
                "quantity_limit": 10,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "name",
            "A ticket type with this name already exists for this event.",
        )

    # --- EMS-F-014: Capacity Control & Concurrency Tests (TC-Evt-05 / TC-05) ---

    def test_system_prevents_registration_beyond_event_capacity(self):
        """EMS-F-014: Registration attempt beyond event capacity is rejected with Sold Out."""
        self.event.status = Event.Status.PUBLISHED
        self.event.capacity = 2
        self.event.save()

        # Attendee 1 registers 2 tickets (consuming all capacity)
        reg1 = create_registration(
            user=self.attendee,
            event_id=self.event.pk,
            quantity=2,
        )
        self.assertEqual(reg1.status, Registration.Status.PENDING)

        self.event.refresh_from_db()
        self.assertEqual(self.event.remaining_capacity, 0)
        self.assertTrue(self.event.is_sold_out)

        # Attendee 2 attempts to register another ticket -> Sold Out rejected
        other_attendee = User.objects.create_user(
            username="other_attendee",
            password="StrongPass123!",
        )
        with self.assertRaises(ValueError) as ctx:
            create_registration(
                user=other_attendee,
                event_id=self.event.pk,
                quantity=1,
            )
        self.assertIn("Sold Out", str(ctx.exception))

    def test_system_prevents_registration_beyond_ticket_type_capacity(self):
        """EMS-F-014: Registration beyond specific ticket tier limit is rejected."""
        self.event.status = Event.Status.PUBLISHED
        self.event.capacity = 100
        self.event.save()

        vip = TicketType.objects.create(
            event=self.event,
            name="VIP Limited",
            price=Decimal("5000.00"),
            quantity_limit=1,
        )

        # First registration takes the 1 VIP ticket
        create_registration(
            user=self.attendee,
            event_id=self.event.pk,
            ticket_type_id=vip.pk,
            quantity=1,
        )
        vip.refresh_from_db()
        self.assertEqual(vip.sold_count, 1)
        self.assertTrue(vip.is_sold_out)

        # Second registration for VIP must be rejected as Sold Out
        other_user = User.objects.create_user(
            username="vip_aspirant",
            password="StrongPass123!",
        )
        with self.assertRaises(ValueError) as ctx:
            create_registration(
                user=other_user,
                event_id=self.event.pk,
                ticket_type_id=vip.pk,
                quantity=1,
            )
        self.assertIn("Sold Out: Ticket type capacity exceeded", str(ctx.exception))

    def test_sold_out_displayed_on_event_page_when_capacity_reached(self):
        """EMS-F-014: 'Sold Out' is prominently displayed on the event detail view."""
        self.event.status = Event.Status.PUBLISHED
        self.event.capacity = 1
        self.event.save()

        create_registration(
            user=self.attendee,
            event_id=self.event.pk,
            quantity=1,
        )

        response = self.client.get(
            reverse("event_detail", kwargs={"pk": self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sold Out")

    def test_cancellation_and_refund_restores_capacity(self):
        """EMS-F-014: Refunding/cancelling a registration frees capacity for others."""
        self.event.status = Event.Status.PUBLISHED
        self.event.capacity = 1
        self.event.ticket_price = Decimal("500.00")
        self.event.save()

        ticket_type = TicketType.objects.create(
            event=self.event,
            name="Solo Tier",
            price=Decimal("500.00"),
            quantity_limit=1,
        )

        # Register and pay
        reg = create_registration(
            user=self.attendee,
            event_id=self.event.pk,
            ticket_type_id=ticket_type.pk,
            quantity=1,
        )
        payment = process_payment(reg.pk)

        self.event.refresh_from_db()
        self.assertTrue(self.event.is_sold_out)

        # Process refund -> cancels registration
        process_refund(payment.pk, "Requested refund")

        self.event.refresh_from_db()
        ticket_type.refresh_from_db()

        self.assertEqual(self.event.remaining_capacity, 1)
        self.assertFalse(self.event.is_sold_out)
        self.assertEqual(ticket_type.sold_count, 0)
        self.assertFalse(ticket_type.is_sold_out)

    def test_cannot_register_for_unpublished_event(self):
        """EMS-F-014 / EMS-F-012: Registration attempts on unpublished events fail."""
        self.event.status = Event.Status.DRAFT
        self.event.save()

        with self.assertRaises(ValueError) as ctx:
            create_registration(
                user=self.attendee,
                event_id=self.event.pk,
                quantity=1,
            )
        self.assertIn("unpublished", str(ctx.exception))


class EventAPITests(TestCase):
    """SAD 4.3 REST API Endpoints Verification."""

    def setUp(self):
        self.organizer = User.objects.create_user(
            username="api_organizer",
            email="organizer@api.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.organizer,
            role=Role.ORGANIZER,
            email_verified=True,
        )

        self.attendee = User.objects.create_user(
            username="api_attendee",
            email="attendee@api.test",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.attendee,
            role=Role.ATTENDEE,
            email_verified=True,
        )

        self.event = Event.objects.create(
            organizer=self.organizer,
            name="API Summit",
            title="API Summit",
            venue="Silicon Hub",
            date=timezone.now() + timedelta(days=10),
            ticket_price=Decimal("200.00"),
            capacity=100,
            status=Event.Status.PUBLISHED,
        )

    def test_api_create_event_as_organizer(self):
        """POST /api/v1/events/ - Organizer creates event in Draft status (201)."""
        self.client.force_login(self.organizer)
        date_str = (timezone.now() + timedelta(days=20)).isoformat()
        response = self.client.post(
            reverse("api_events_list_create"),
            {
                "title": "Backend Engineering Conference",
                "category": "Technology",
                "venue": "Convention Center Hall A",
                "date": date_str,
                "capacity": 200,
                "ticket_price": "500.00",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Event.Status.DRAFT)
        self.assertEqual(response.data["organizer"], "api_organizer")

    def test_api_create_event_forbidden_for_attendee(self):
        """POST /api/v1/events/ - Attendee gets 403 Forbidden."""
        self.client.force_login(self.attendee)
        response = self.client.post(
            reverse("api_events_list_create"),
            {
                "title": "Attendee Event",
                "venue": "Somewhere",
                "date": (timezone.now() + timedelta(days=10)).isoformat(),
                "capacity": 50,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_api_search_published_events(self):
        """GET /api/v1/events/ - Public search returns only published events (200)."""
        # Create a draft event
        Event.objects.create(
            organizer=self.organizer,
            name="Secret Unreleased Event",
            title="Secret Unreleased Event",
            venue="Secret Lab",
            date=timezone.now() + timedelta(days=5),
            capacity=10,
            status=Event.Status.DRAFT,
        )

        response = self.client.get(reverse("api_events_list_create"))
        self.assertEqual(response.status_code, 200)

        # Published event should be in response, draft event should not
        titles = [e["title"] for e in response.data]
        self.assertIn("API Summit", titles)
        self.assertNotIn("Secret Unreleased Event", titles)

    def test_api_publish_and_unpublish_event(self):
        """POST /api/v1/events/{id}/publish/ & unpublish/ - Owning organizer."""
        draft_event = Event.objects.create(
            organizer=self.organizer,
            name="Draft API Event",
            title="Draft API Event",
            venue="Online",
            date=timezone.now() + timedelta(days=12),
            capacity=150,
            status=Event.Status.DRAFT,
        )

        self.client.force_login(self.organizer)

        # Publish
        pub_res = self.client.post(
            reverse("api_events_publish", kwargs={"pk": draft_event.pk})
        )
        self.assertEqual(pub_res.status_code, 200)
        self.assertEqual(pub_res.data["status"], Event.Status.PUBLISHED)

        # Unpublish
        unpub_res = self.client.post(
            reverse("api_events_unpublish", kwargs={"pk": draft_event.pk})
        )
        self.assertEqual(unpub_res.status_code, 200)
        self.assertEqual(unpub_res.data["status"], Event.Status.UNPUBLISHED)

    def test_api_add_ticket_types(self):
        """POST /api/v1/events/{id}/ticket-types/ - Owning organizer adds ticket tier."""
        self.client.force_login(self.organizer)
        response = self.client.post(
            reverse("api_events_ticket_types", kwargs={"pk": self.event.pk}),
            {
                "name": "General Admission",
                "price": "200.00",
                "quantity_limit": 50,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "General Admission")
        self.assertEqual(response.data["quantity_limit"], 50)

    def test_api_registration_capacity_exceeded_returns_409(self):
        """POST /api/v1/events/{id}/registrations/ - Returns 409 Conflict when Sold Out."""
        self.event.capacity = 1
        self.event.save()

        self.client.force_login(self.attendee)

        # First registration succeeds
        res1 = self.client.post(
            reverse("api_events_registrations", kwargs={"pk": self.event.pk}),
            {"quantity": 1},
            content_type="application/json",
        )
        self.assertEqual(res1.status_code, 201)

        # Second registration exceeds capacity -> 409 Conflict
        res2 = self.client.post(
            reverse("api_events_registrations", kwargs={"pk": self.event.pk}),
            {"quantity": 1},
            content_type="application/json",
        )
        self.assertEqual(res2.status_code, 409)
        self.assertEqual(res2.data["code"], "CAPACITY_EXCEEDED")
        self.assertIn("Sold Out", res2.data["message"])


class ConcurrentCapacityTests(TransactionTestCase):
    """TC-05: Capacity and concurrent registration. (EMS-F-014, EMS-NF-003)."""

    def test_concurrent_registrations_for_last_ticket(self):
        """
        TC-05 Preconditions: Published event with one remaining ticket.
        Multiple requests submitted concurrently. Exactly 1 confirmed, others receive Sold Out.
        Capacity never negative, no duplicate registration.
        """
        event = Event.objects.create(
            name="Exclusive Keynote",
            title="Exclusive Keynote",
            venue="Main Auditorium",
            date=timezone.now() + timedelta(days=5),
            capacity=1,
            ticket_price=Decimal("100.00"),
            status=Event.Status.PUBLISHED,
        )

        user_a = User.objects.create_user(
            username="concurrent_user_a",
            password="StrongPass123!",
        )
        user_b = User.objects.create_user(
            username="concurrent_user_b",
            password="StrongPass123!",
        )

        results = []
        errors = []

        def attempt_registration(user):
            connection.close()
            try:
                reg = create_registration(user, event.pk, quantity=1)
                results.append(reg)
            except ValueError as err:
                errors.append(str(err))
            finally:
                connection.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(attempt_registration, user_a)
            f2 = executor.submit(attempt_registration, user_b)
            concurrent.futures.wait([f1, f2])

        self.assertEqual(len(results), 1, "Exactly one registration must succeed")
        self.assertEqual(len(errors), 1, "The competing registration must fail")
        self.assertIn("Sold Out", errors[0])

        event.refresh_from_db()
        self.assertEqual(event.remaining_capacity, 0)
        self.assertTrue(event.is_sold_out)
        self.assertEqual(event.registered_attendees_count, 1)
