"""EMS-F-040 / EMS-F-041 / Test Plan TC-09, using a controlled mock email service."""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from events.models import Event, Registration
from events.notifications.constants import (
    MAX_ATTEMPTS,
    NotificationStatus as S,
    NotificationType as T,
)
from events.notifications.email_service import MockEmailBackend
from events.notifications.models import Notification
from events.notifications.services import (
    cancel_reminders,
    deliver_notification,
    notify_registration_confirmed,
    requeue_stale,
    schedule_due_reminders,
)
from events.notifications.tasks import backoff_seconds, send_notification


def make_reg(hours_to_start=100, status="confirmed", registered_hours_before_start=200):
    now = timezone.now()
    event = Event.objects.create(
        title="Django Conf",
        date=now + timedelta(hours=hours_to_start),
        status=Event.Status.PUBLISHED,
        venue="Hall A",
    )
    user = User.objects.create_user(
        username=f"attendee-{Registration.objects.count()}",
        email="a@x.com",
    )
    status_value = {
        "confirmed": Registration.Status.CONFIRMED,
        "pending": Registration.Status.PENDING,
        "cancelled": Registration.Status.CANCELLED,
    }.get(status, status.upper())
    return Registration.objects.create(
        event=event,
        user=user,
        status=status_value,
        confirmed_at=event.date - timedelta(hours=registered_hours_before_start),
    )


class Base(TestCase):
    def setUp(self):
        MockEmailBackend.reset()


class ConfirmationTests(Base):
    def test_confirmed_registration_sends_one_email_after_commit(self):
        reg = make_reg()
        with self.captureOnCommitCallbacks(execute=True):
            n = notify_registration_confirmed(reg.pk)
        n.refresh_from_db()
        self.assertEqual(n.status, S.SENT)
        self.assertEqual(len(MockEmailBackend.outbox), 1)
        mail = MockEmailBackend.outbox[0]
        self.assertEqual(mail["to"], "a@x.com")
        self.assertIn("Django Conf", mail["subject"])
        self.assertIn(f"REG-{reg.pk}", mail["text"])
        self.assertIn("UTC", mail["text"])

    def test_not_sent_before_commit(self):
        reg = make_reg()
        with self.captureOnCommitCallbacks(execute=False):
            notify_registration_confirmed(reg.pk)
        self.assertEqual(len(MockEmailBackend.outbox), 0)

    def test_pending_or_failed_registration_gets_no_confirmation(self):
        for status in ("pending", "failed", "cancelled"):
            reg = make_reg(status=status)
            with self.captureOnCommitCallbacks(execute=True):
                self.assertIsNone(notify_registration_confirmed(reg.pk))
        self.assertEqual(len(MockEmailBackend.outbox), 0)

    def test_no_duplicate_confirmation(self):
        reg = make_reg()
        for _ in range(3):
            with self.captureOnCommitCallbacks(execute=True):
                notify_registration_confirmed(reg.pk)
        self.assertEqual(len(MockEmailBackend.outbox), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_unknown_registration_does_not_raise(self):
        self.assertIsNone(notify_registration_confirmed(999999))


class FailureHandlingTests(Base):
    def _queued(self):
        reg = make_reg()
        return Notification.objects.create(
            notification_type=T.CONFIRMATION, registration_id=reg.pk,
            recipient_email="a@x.com", idempotency_key=f"confirmation:{reg.pk}")

    def test_transient_failure_is_retried_then_succeeds(self):
        n = self._queued()
        MockEmailBackend.fail_next(2)
        self.assertEqual(deliver_notification(n.pk), "retry")
        self.assertEqual(deliver_notification(n.pk), "retry")
        self.assertEqual(deliver_notification(n.pk), "sent")
        n.refresh_from_db()
        self.assertEqual((n.status, n.attempts), (S.SENT, 3))

    def test_gives_up_after_max_attempts(self):
        n = self._queued()
        MockEmailBackend.fail_next(MAX_ATTEMPTS + 2)
        results = [deliver_notification(n.pk) for _ in range(MAX_ATTEMPTS)]
        self.assertEqual(results[-1], "failed")
        n.refresh_from_db()
        self.assertEqual(n.status, S.FAILED)
        self.assertEqual(n.error_category, "provider_unavailable")
        self.assertEqual(deliver_notification(n.pk), "skipped")   # terminal state

    def test_permanent_failure_is_not_retried(self):
        n = self._queued()
        MockEmailBackend.fail_next(1, transient=False, category="invalid_recipient")
        self.assertEqual(deliver_notification(n.pk), "failed")

    def test_celery_task_requests_retry_with_backoff_then_sends(self):
        from celery.exceptions import Retry
        n = self._queued()
        MockEmailBackend.fail_next(1)
        with self.assertRaises(Retry) as ctx:             # eager mode surfaces the retry request
            send_notification.delay(n.pk)
        self.assertEqual(ctx.exception.when, 30)          # first backoff = 30s
        self.assertEqual(send_notification.delay(n.pk).get(), "sent")   # the retried run
        n.refresh_from_db()
        self.assertEqual((n.status, n.attempts), (S.SENT, 2))

    def test_backoff_grows_and_is_capped(self):
        self.assertEqual([backoff_seconds(i) for i in (1, 2, 3)], [30, 60, 120])
        self.assertEqual(backoff_seconds(50), 3600)

    def test_failed_email_never_breaks_registration_flow(self):
        reg = make_reg()
        MockEmailBackend.fail_next(MAX_ATTEMPTS + 1, transient=False)
        with self.captureOnCommitCallbacks(execute=True):
            n = notify_registration_confirmed(reg.pk)     # must not raise
        n.refresh_from_db()
        self.assertEqual(n.status, S.FAILED)
        reg.refresh_from_db()
        self.assertEqual(reg.status, Registration.Status.CONFIRMED)

    def test_broker_down_leaves_notification_queued_for_sweep(self):
        reg = make_reg()
        with mock.patch(
            "events.notifications.tasks.send_notification.delay",
            side_effect=OSError("redis down"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                n = notify_registration_confirmed(reg.pk)      # must not raise
        n.refresh_from_db()
        self.assertEqual(n.status, S.QUEUED)
        Notification.objects.filter(pk=n.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(requeue_stale(), 1)
        n.refresh_from_db()
        self.assertEqual(n.status, S.SENT)


class ReminderTests(Base):
    def test_48h_reminder_queued_and_sent(self):
        make_reg(hours_to_start=40)
        self.assertEqual(schedule_due_reminders(), 1)
        n = Notification.objects.get()
        self.assertEqual((n.notification_type, n.status), (T.REMINDER_48H, S.SENT))
        self.assertIn("48 hours", MockEmailBackend.outbox[0]["subject"])

    def test_2h_reminder(self):
        make_reg(hours_to_start=1.5)
        schedule_due_reminders()
        self.assertEqual(Notification.objects.get().notification_type, T.REMINDER_2H)
        self.assertIn("2 hours", MockEmailBackend.outbox[0]["subject"])

    def test_both_reminders_over_time_and_no_duplicates(self):
        reg = make_reg(hours_to_start=47)
        now = timezone.now()
        schedule_due_reminders(now)
        schedule_due_reminders(now + timedelta(minutes=5))              # same window again
        schedule_due_reminders(now + timedelta(hours=45.5))             # now inside 2h window
        schedule_due_reminders(now + timedelta(hours=45.6))
        types = sorted(Notification.objects.values_list("notification_type", flat=True))
        self.assertEqual(types, [T.REMINDER_2H, T.REMINDER_48H])
        self.assertEqual(len(MockEmailBackend.outbox), 2)

    def test_event_outside_window_gets_nothing(self):
        make_reg(hours_to_start=100)
        self.assertEqual(schedule_due_reminders(), 0)

    def test_cancelled_registration_gets_no_reminder(self):
        make_reg(hours_to_start=40, status="cancelled")
        self.assertEqual(schedule_due_reminders(), 0)
        self.assertEqual(len(MockEmailBackend.outbox), 0)

    def test_cancelled_event_gets_no_reminder(self):
        reg = make_reg(hours_to_start=40)
        Event.objects.filter(pk=reg.event_id).update(status=Event.Status.CANCELLED)
        self.assertEqual(schedule_due_reminders(), 0)

    def test_cancel_reminders_stops_queued_reminder(self):
        reg = make_reg(hours_to_start=40)
        n = Notification.objects.create(
            notification_type=T.REMINDER_48H, registration_id=reg.pk, recipient_email="a@x.com",
            idempotency_key=f"reminder_48h:{reg.pk}")
        self.assertEqual(cancel_reminders(reg.pk), 1)
        self.assertEqual(deliver_notification(n.pk), "skipped")
        self.assertEqual(len(MockEmailBackend.outbox), 0)

    def test_registration_cancelled_after_queueing_is_not_emailed(self):
        reg = make_reg(hours_to_start=40)
        n = Notification.objects.create(
            notification_type=T.REMINDER_48H, registration_id=reg.pk, recipient_email="a@x.com",
            idempotency_key=f"reminder_48h:{reg.pk}")
        Registration.objects.filter(pk=reg.pk).update(status=Registration.Status.CANCELLED)
        self.assertEqual(deliver_notification(n.pk), "skipped")
        n.refresh_from_db()
        self.assertEqual(n.status, S.CANCELLED)

    def test_last_minute_registration_skips_48h_reminder(self):
        make_reg(hours_to_start=30, registered_hours_before_start=10)
        self.assertEqual(schedule_due_reminders(), 0)

    def test_reminder_uses_current_event_time(self):
        reg = make_reg(hours_to_start=40)
        Event.objects.filter(pk=reg.event_id).update(venue="New Venue")
        schedule_due_reminders()
        self.assertIn("New Venue", MockEmailBackend.outbox[0]["text"])
