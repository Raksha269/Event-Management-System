"""Provider-neutral email boundary configured by settings.NOTIFICATION_EMAIL_BACKEND."""
import uuid
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.module_loading import import_string


class EmailSendError(Exception):
    def __init__(self, message="", category="provider_error", transient=True):
        super().__init__(message)
        self.category = category
        self.transient = transient   # True -> worth retrying


class EmailBackend(ABC):
    @abstractmethod
    def send(self, *, to: str, subject: str, text_body: str, html_body: str) -> str:
        """Send one email. Return a provider message id or raise EmailSendError."""


class DjangoMailBackend(EmailBackend):
    """Uses Django's EMAIL_* settings (SMTP for SendGrid/SES, console in dev)."""

    def send(self, *, to, subject, text_body, html_body):
        try:
            msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [to])
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)
        except Exception as exc:  # network/SMTP problems are retryable
            raise EmailSendError(type(exc).__name__, "provider_unavailable", True) from exc
        return f"django-{uuid.uuid4()}"


class MockEmailBackend(EmailBackend):
    """In-memory backend for tests. Inspect MockEmailBackend.outbox."""
    outbox: list = []
    _failures: list = []

    @classmethod
    def reset(cls):
        cls.outbox = []
        cls._failures = []

    @classmethod
    def fail_next(cls, times=1, *, transient=True, category="provider_unavailable"):
        cls._failures = [(transient, category)] * times

    def send(self, *, to, subject, text_body, html_body):
        if self._failures:
            transient, category = type(self)._failures.pop(0)
            raise EmailSendError("mock failure", category, transient)
        message_id = f"mock-{len(self.outbox) + 1}"
        type(self).outbox.append({"to": to, "subject": subject, "text": text_body,
                                  "html": html_body, "message_id": message_id})
        return message_id


def get_backend() -> EmailBackend:
    return import_string(settings.NOTIFICATION_EMAIL_BACKEND)()
