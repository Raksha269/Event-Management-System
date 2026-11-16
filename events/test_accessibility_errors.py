from html.parser import HTMLParser
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event, Registration, TicketType, UserProfile


class FormMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = set()
        self.invalid_descriptions = []
        self.summaries = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
            if attrs.get('id') in {'error-summary', 'registration-error-summary'}:
                self.summaries.append(attrs)
        if attrs.get('aria-invalid') == 'true':
            self.invalid_descriptions.append(attrs.get('aria-describedby', '').split())


class HeadingMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.levels = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if len(tag) == 2 and tag[0] == 'h' and tag[1].isdigit():
            self.levels.append(int(tag[1]))


class AccessibleErrorTests(TestCase):
    def assert_error_descriptions_resolve(self, response, summary_id='error-summary'):
        self.assertEqual(response.status_code, 200)
        markup = FormMarkup(response.content.decode())
        self.assertIn(summary_id, markup.ids)
        self.assertTrue(markup.invalid_descriptions)
        for descriptions in markup.invalid_descriptions:
            self.assertTrue(descriptions)
            self.assertTrue(set(descriptions) <= markup.ids)

    def test_registration_errors_have_resolvable_descriptions(self):
        response = self.client.post('/accounts/register/', {})
        self.assert_error_descriptions_resolve(response)
        self.assertFalse(User.objects.exists())

    def test_organizer_errors_have_resolvable_descriptions(self):
        user = User.objects.create_user(username='organizer')
        UserProfile.objects.update_or_create(
            user=user, defaults={'role': 'organizer', 'email_verified': True}
        )
        self.client.force_login(user)
        self.assert_error_descriptions_resolve(self.client.post('/events/create/', {}))

    def test_ticket_type_errors_have_resolvable_descriptions_and_focused_summary(self):
        user = User.objects.create_user(username='ticket-organizer')
        UserProfile.objects.update_or_create(
            user=user, defaults={'role': 'organizer', 'email_verified': True}
        )
        event = Event.objects.create(
            organizer=user, title='Ticket form accessibility', venue='Test hall',
            date=timezone.now() + timedelta(days=30), capacity=10,
        )
        self.client.force_login(user)

        response = self.client.post(f'/events/{event.pk}/tickets/', {})

        self.assert_error_descriptions_resolve(response)
        markup = FormMarkup(response.content.decode())
        self.assertEqual(len(markup.summaries), 1)
        self.assertEqual(markup.summaries[0].get('role'), 'alert')
        self.assertEqual(markup.summaries[0].get('tabindex'), '-1')
        self.assertContains(response, "document.getElementById('error-summary').focus()")

    def test_ticket_capacity_validation_error_is_associated_with_quantity_control(self):
        user = User.objects.create_user(username='capacity-organizer')
        UserProfile.objects.update_or_create(
            user=user, defaults={'role': 'organizer', 'email_verified': True}
        )
        event = Event.objects.create(
            organizer=user, title='Ticket capacity accessibility', venue='Test hall',
            date=timezone.now() + timedelta(days=30), capacity=10,
        )
        TicketType.objects.create(
            event=event, name='Existing tier', quantity_limit=8, price=0,
        )
        self.client.force_login(user)

        response = self.client.post(
            f'/events/{event.pk}/tickets/',
            {'name': 'Additional tier', 'price': '0', 'quantity_limit': '5'},
        )

        self.assert_error_descriptions_resolve(response)
        self.assertContains(response, 'cannot exceed event capacity')

    def test_event_registration_errors_are_announced_and_linked_to_fields(self):
        organizer = User.objects.create_user(username='registration-organizer')
        UserProfile.objects.update_or_create(
            user=organizer, defaults={'role': 'organizer', 'email_verified': True}
        )
        attendee = User.objects.create_user(username='registration-attendee')
        UserProfile.objects.update_or_create(
            user=attendee, defaults={'role': 'attendee', 'email_verified': True}
        )
        event = Event.objects.create(
            organizer=organizer, title='Registration error accessibility',
            venue='Test hall', date=timezone.now() + timedelta(days=30),
            capacity=10, status=Event.Status.PUBLISHED,
        )
        self.client.force_login(attendee)

        response = self.client.post(
            reverse('event_register', kwargs={'pk': event.pk}),
            {'quantity': '0', 'idempotency_key': 'local-test-key'},
        )

        self.assert_error_descriptions_resolve(
            response, summary_id='registration-error-summary'
        )
        markup = FormMarkup(response.content.decode())
        self.assertEqual(len(markup.summaries), 1)
        self.assertEqual(markup.summaries[0].get('role'), 'alert')
        self.assertEqual(markup.summaries[0].get('tabindex'), '-1')
        self.assertContains(
            response,
            "document.getElementById('registration-error-summary').focus()",
        )
        self.assertFalse(Registration.objects.exists())

    def test_registration_service_failure_uses_an_alert_role(self):
        organizer = User.objects.create_user(username='full-event-organizer')
        UserProfile.objects.update_or_create(
            user=organizer, defaults={'role': 'organizer', 'email_verified': True}
        )
        attendee = User.objects.create_user(username='full-event-attendee')
        UserProfile.objects.update_or_create(
            user=attendee, defaults={'role': 'attendee', 'email_verified': True}
        )
        prior_attendee = User.objects.create_user(username='prior-attendee')
        event = Event.objects.create(
            organizer=organizer, title='Full event alert accessibility',
            venue='Test hall', date=timezone.now() + timedelta(days=30),
            capacity=1, status=Event.Status.PUBLISHED,
        )
        Registration.objects.create(
            user=prior_attendee, event=event, quantity=1,
            status=Registration.Status.CONFIRMED,
        )
        self.client.force_login(attendee)

        response = self.client.post(
            reverse('event_register', kwargs={'pk': event.pk}),
            {'quantity': '1', 'idempotency_key': 'local-test-key'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'Sold Out')

    def test_selected_empty_states_have_no_skipped_heading_levels(self):
        attendee = User.objects.create_user(username='heading-attendee')
        UserProfile.objects.update_or_create(
            user=attendee, defaults={'role': 'attendee', 'email_verified': True}
        )
        organizer = User.objects.create_user(username='heading-organizer')
        UserProfile.objects.update_or_create(
            user=organizer, defaults={'role': 'organizer', 'email_verified': True}
        )

        responses = [self.client.get(reverse('discover_events'))]
        self.client.force_login(attendee)
        responses.append(self.client.get(reverse('attendee_dashboard')))
        self.client.force_login(organizer)
        responses.append(self.client.get(reverse('organizer_dashboard')))

        for response in responses:
            self.assertEqual(response.status_code, 200)
            headings = HeadingMarkup(response.content.decode()).levels
            self.assertTrue(headings)
            self.assertEqual(headings[0], 1)
            self.assertFalse(
                any(
                    current > previous + 1
                    for previous, current in zip(headings, headings[1:])
                ),
                headings,
            )

    def test_admin_filters_and_per_user_actions_have_accessible_names(self):
        admin = User.objects.create_user(username='a11y-admin', is_staff=True)
        UserProfile.objects.update_or_create(
            user=admin, defaults={'role': 'administrator', 'email_verified': True}
        )
        User.objects.create_user(username='target-user')
        self.client.force_login(admin)

        response = self.client.get(reverse('admin_user_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Search users by username or email"')
        self.assertContains(response, 'aria-label="Filter users by role"')
        self.assertContains(response, 'aria-label="Role for target-user"')
        self.assertContains(response, 'aria-label="Update role for target-user"')
        self.assertContains(response, 'aria-label="Deactivate target-user"')

        alerts = self.client.get(reverse('admin_alerts_list'))
        self.assertEqual(alerts.status_code, 200)
        self.assertContains(alerts, 'aria-label="Filter alerts by severity"')
        self.assertContains(alerts, 'aria-label="Filter alerts by type"')

    def test_ticket_capacity_summary_reports_actual_unallocated_quantity(self):
        user = User.objects.create_user(username='organizer')
        UserProfile.objects.update_or_create(
            user=user, defaults={'role': 'organizer', 'email_verified': True}
        )
        event = Event.objects.create(
            organizer=user, title='Local capacity check', venue='Test hall',
            date=timezone.now() + timedelta(days=30), capacity=10,
        )
        self.client.force_login(user)
        for allocated in (0, 4, 10):
            with self.subTest(allocated=allocated):
                event.ticket_types.all().delete()
                if allocated:
                    TicketType.objects.create(
                        event=event, name='General', quantity_limit=allocated, price=0,
                    )
                response = self.client.get(f'/events/{event.pk}/tickets/')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['unallocated_capacity'], 10 - allocated)
                self.assertContains(response, f'{10 - allocated} tickets')
