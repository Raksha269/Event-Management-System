from datetime import timedelta
import logging
import re

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Payment, Registration, SecurityAlert

audit_log = logging.getLogger("ems.audit")
security_log = logging.getLogger("ems.security")

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
ABNORMAL_REGISTRATION_THRESHOLD = 5  # registrations within 1 minute on same event


def record_security_alert(alert_type, severity, details, target_user=None):
    """
    Log and create an administrator-visible security alert (EMS-SR-005).
    """
    alert = SecurityAlert.objects.create(
        alert_type=alert_type,
        severity=severity,
        target_user=target_user,
        details=details,
    )
    security_log.warning(
        "security_alert type=%s severity=%s user=%s details=%s",
        alert_type,
        severity,
        getattr(target_user, "username", "N/A"),
        details,
    )
    return alert


def check_account_lockout(user):
    """
    Check if user is currently locked out due to repeated failed logins (EMS-F-004, EMS-SR-005).
    """
    if getattr(user, "is_locked", False):
        return True, "Account temporarily locked. Please try again later."
    return False, None


def track_login_failure(username_or_email, request=None):
    """
    Track a failed login attempt, update counter, and trigger lockout/alert if threshold is reached.
    """
    User = get_user_model()
    user = (
        User.objects.filter(username=username_or_email).first()
        or User.objects.filter(email__iexact=username_or_email).first()
    )

    if user is None:
        audit_log.warning(
            "login_failure username=%s reason=user_not_found", username_or_email
        )
        return False, "Invalid username or password."

    # Check if already locked
    is_locked, msg = check_account_lockout(user)
    if is_locked:
        audit_log.warning("login_attempt_on_locked_account user_id=%s", user.pk)
        return False, msg

    user.failed_login_attempts += 1

    if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = timezone.now() + LOCKOUT_DURATION
        record_security_alert(
            alert_type=SecurityAlert.AlertType.ACCOUNT_LOCKOUT,
            severity=SecurityAlert.Severity.HIGH,
            details=(
                f"Account '{user.username}' locked for 15 minutes after "
                f"{user.failed_login_attempts} consecutive failed login attempts."
            ),
            target_user=user,
        )
        security_log.error(
            "account_lockout user_id=%s failed_attempts=%s",
            user.pk,
            user.failed_login_attempts,
        )
        return False, "Account temporarily locked. Please try again later."

    if user.failed_login_attempts >= 3:
        record_security_alert(
            alert_type=SecurityAlert.AlertType.FAILED_LOGIN_BURST,
            severity=SecurityAlert.Severity.MEDIUM,
            details=(
                f"Suspicious login failure burst: '{user.username}' has "
                f"{user.failed_login_attempts} failed login attempts."
            ),
            target_user=user,
        )

    return False, "Invalid username or password."


def record_login_success(user):
    """
    Clear failed login counters on successful authentication.
    """
    if getattr(user, "failed_login_attempts", 0) > 0 or getattr(
        user, "locked_until", None
    ):
        user.failed_login_attempts = 0
        user.locked_until = None
    audit_log.info(
        "login_success user_id=%s role=%s",
        user.pk,
        getattr(user, "role", "unknown"),
    )


def track_abnormal_registration(event, user=None, count=1):
    """
    Monitor registration velocity and alert on abnormal spikes (EMS-SR-005).
    """
    one_minute_ago = timezone.now() - timedelta(minutes=1)
    recent_count = Registration.objects.filter(
        event=event, created_at__gte=one_minute_ago
    ).count()

    if recent_count >= ABNORMAL_REGISTRATION_THRESHOLD:
        record_security_alert(
            alert_type=SecurityAlert.AlertType.ABNORMAL_REGISTRATION_RATE,
            severity=SecurityAlert.Severity.HIGH,
            details=(
                f"Abnormal registration spike on event '{event.title or event.name}' (id={event.pk}): "
                f"{recent_count} registrations created within the last 60 seconds."
            ),
            target_user=user,
        )


def verify_tls_version(protocol_name):
    """
    Verify network communication protocol complies with TLS 1.2 or higher (EMS-SR-001).
    Rejects insecure legacy protocols (SSLv2, SSLv3, TLS 1.0, TLS 1.1).
    """
    raw = protocol_name.strip().upper().replace(" ", "").replace("_", ".")

    # Reject SSL entirely
    if raw.startswith("SSL"):
        return (
            False,
            f"Protocol '{protocol_name}' is deprecated and rejected. Minimum required is TLS 1.2.",
        )

    # Match TLS version: e.g. TLS1.0, TLSv1.0, TLS1, TLS1.2, TLSv1.3
    match = re.match(r"^TLS(?:V)?(\d+)(?:\.(\d+))?$", raw)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) is not None else 0
        if (major < 1) or (major == 1 and minor < 2):
            return (
                False,
                f"Protocol '{protocol_name}' is deprecated and rejected. Minimum required is TLS 1.2.",
            )
        elif (major == 1 and minor >= 2) or (major > 1):
            return (
                True,
                f"Protocol '{protocol_name}' satisfies TLS 1.2+ requirement.",
            )

    return (
        False,
        f"Unknown or unverified protocol '{protocol_name}'. Minimum required is TLS 1.2.",
    )


def inspect_payment_data_storage():
    """
    Verify PCI-DSS compliant storage: inspect database fields and records (EMS-SR-002).
    Confirms no raw credit card numbers (PANs) or CVVs are stored anywhere.
    """
    forbidden_terms = [
        "card_number",
        "credit_card",
        "pan",
        "cvv",
        "cvc",
        "card_code",
        "track_data",
        "exp_month",
        "exp_year",
    ]

    events_models = apps.get_app_config("events").get_models()
    disallowed_fields_found = []

    for model in events_models:
        for field in model._meta.get_fields():
            field_name = field.name.lower()
            for term in forbidden_terms:
                if term in field_name:
                    disallowed_fields_found.append(
                        f"{model.__name__}.{field.name}"
                    )

    # Check Payment model specifically: must only use tokens/UUIDs
    payment_fields = [f.name for f in Payment._meta.get_fields()]
    has_token_field = "transaction_id" in payment_fields

    is_compliant = (len(disallowed_fields_found) == 0) and has_token_field

    return is_compliant, {
        "compliant": is_compliant,
        "token_field_present": has_token_field,
        "disallowed_fields": disallowed_fields_found,
        "payment_fields": payment_fields,
    }


def verify_password_hashing(user):
    """
    Verify user password is encrypted using a modern, salted hashing algorithm (EMS-SR-003).
    """
    password = user.password

    # Plaintext detection
    if not password or len(password) < 20 or "$" not in password:
        return False, "Password appears to be stored in plaintext."

    # Parse Django password hash format: algorithm$iterations$salt$hash
    parts = password.split("$")
    algorithm = parts[0]

    modern_algorithms = [
        "pbkdf2_sha256",
        "pbkdf2_sha512",
        "argon2",
        "bcrypt",
        "bcrypt_sha256",
    ]

    if any(alg in algorithm.lower() for alg in modern_algorithms):
        return True, algorithm

    return False, f"Insecure or outdated algorithm detected: '{algorithm}'"
