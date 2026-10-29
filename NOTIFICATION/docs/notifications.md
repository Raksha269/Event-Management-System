# Notifications (EMS-F-040 / EMS-F-041)

## For the registration/payment owners (#5, #6)
```python
from notifications.services import notify_registration_confirmed, cancel_reminders

# after payment succeeded and the registration is saved as status="confirmed":
notify_registration_confirmed(registration.pk)

# when a registration is cancelled:
cancel_reminders(registration.pk)
```
Both calls are safe: they never raise and send only after the DB transaction commits.
Required status vocabulary: pending, confirmed, failed, cancelled, refunded.

## Connecting the real models (one file)
Edit `notifications/adapters.py`: import the real Event/Registration models and map
their fields into `RegistrationData`. Then delete the `standins` app.

## Running
    pip install -r requirements.txt
    python manage.py migrate && python manage.py test
    celery -A ems worker -l info      # needs Redis
    celery -A ems beat -l info        # reminders every 5 minutes

## Email provider
Default sends via Django's EMAIL_* settings (SendGrid/SES SMTP work by configuration).
To add a native SDK, subclass `EmailBackend` in `email_service.py` and point
`NOTIFICATION_EMAIL_BACKEND` at it.
