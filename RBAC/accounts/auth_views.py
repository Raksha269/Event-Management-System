import logging
from datetime import timedelta
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from .models import User

audit_log = logging.getLogger("ems.audit")
security_log = logging.getLogger("ems.security")
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
GENERIC_LOGIN_ERROR = "Invalid email or password."
LOCKOUT_ERROR = "Account temporarily locked. Please try again later."

@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """Email/password session login with five failures and a 15-minute lockout."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password:
            return JsonResponse({"error": GENERIC_LOGIN_ERROR}, status=400)

        user = User.objects.filter(email__iexact=email.strip()).first()
        if user is None:
            # Do a dummy backend check to reduce obvious timing-based enumeration.
            authenticate(request=request._request, username=email.strip(), password=password)
            audit_log.warning("login_failure reason=invalid_credentials")
            return JsonResponse({"error": GENERIC_LOGIN_ERROR}, status=401)

        now = timezone.now()
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            if user.locked_until and user.locked_until > now:
                audit_log.warning("login_rejected user_id=%s reason=account_locked", user.pk)
                return JsonResponse({"error": LOCKOUT_ERROR}, status=423)
            if user.locked_until and user.locked_until <= now:
                user.locked_until = None
                user.failed_login_attempts = 0
                user.save(update_fields=["locked_until", "failed_login_attempts"])

            authenticated = authenticate(request=request._request, username=user.get_username(), password=password)
            if authenticated is None:
                user.failed_login_attempts += 1
                fields = ["failed_login_attempts"]
                if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                    user.locked_until = now + LOCKOUT_DURATION
                    fields.append("locked_until")
                user.save(update_fields=fields)
                audit_log.warning("login_failure user_id=%s failed_attempts=%s", user.pk, user.failed_login_attempts)
                if user.locked_until and user.locked_until > now:
                    security_log.error("account_lockout user_id=%s failed_attempts=%s duration_seconds=%s",
                                       user.pk, user.failed_login_attempts, int(LOCKOUT_DURATION.total_seconds()))
                return JsonResponse({"error": GENERIC_LOGIN_ERROR}, status=401)

            if user.failed_login_attempts or user.locked_until:
                user.failed_login_attempts = 0
                user.locked_until = None
                user.save(update_fields=["failed_login_attempts", "locked_until"])

        login(request._request, authenticated)
        audit_log.info("login_success user_id=%s role=%s", authenticated.pk, authenticated.role)
        return JsonResponse({"message": "Login successful.", "user": {
            "id": authenticated.pk, "username": authenticated.username,
            "email": authenticated.email, "role": authenticated.role,
        }}, status=200)
