# Notifications (EMS-F-040 / EMS-F-041)

The notification app is integrated at `events/notifications` and uses the
main project's event and registration models.

## Registration/payment integration
```python
from events.notifications.services import notify_registration_confirmed, cancel_reminders

# after payment succeeds and the registration is saved as CONFIRMED:
notify_registration_confirmed(registration.pk)

# when a registration is cancelled or refunded:
cancel_reminders(registration.pk)
```
Payment and refund services already make these calls. Confirmation email dispatch
waits until the payment transaction commits; notification failures do not undo a
successful registration.

## Running
Run the normal project commands from the repository root:

    pip install -r requirements.txt
    python manage.py migrate
    python manage.py test
    celery -A config worker -l info --pool=solo   # needs Redis; solo pool supports Windows
    celery -A config beat -l info     # reminders every 5 minutes

## Email provider
Default sends via Django's EMAIL_* settings (SendGrid/SES SMTP work by configuration).
To add a native SDK, subclass `EmailBackend` in
`events/notifications/email_service.py` and configure `NOTIFICATION_EMAIL_BACKEND`.
