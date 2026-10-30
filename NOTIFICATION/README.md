# Notifications integration

Notifications are now part of the main project under `events/notifications` and
use the main `events` models. Configuration is in `config/settings.py`; run
migrations and tests from the repository root.

See [`events/notifications/docs/notifications.md`](../events/notifications/docs/notifications.md).

    pip install -r requirements.txt
    python manage.py migrate
    python manage.py test
