
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import login, logout
from .forms import RegistrationForm, GatherLoginForm

from .forms import RegistrationForm
from .models import UserProfile


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)

                # The account cannot be used until email verification.
                user.is_active = False
                user.save()

                verification_token = secrets.token_urlsafe(32)

                UserProfile.objects.create(
                    user=user,
                    email_verified=False,
                    verification_token=verification_token,
                )

                verification_url = request.build_absolute_uri(
                    reverse(
                        "verify_email",
                        kwargs={"token": verification_token},
                    )
                )

                transaction.on_commit(
                    lambda: send_mail(
                        subject="Verify your Gather account",
                        message=(
                            f"Hi {user.username},\n\n"
                            "Please verify your email address using this link:\n"
                            f"{verification_url}\n\n"
                            "If you did not create this account, you can ignore this email."
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                )

            messages.success(
                request,
                "Registration successful! Check the terminal for your email verification link.",
            )
            return redirect("register")
    else:
        form = RegistrationForm()

    return render(request, "events/register.html", {"form": form})


def verify_email(request, token):
    profile = UserProfile.objects.filter(
        verification_token=token,
        email_verified=False,
    ).select_related("user").first()

    if profile is None:
        return render(
            request,
            "events/verification_result.html",
            {
                "success": False,
                "message": (
                    "This verification link is invalid or has already been used."
                ),
            },
            status=400,
        )

    profile.email_verified = True
    profile.verification_token = None
    profile.save(update_fields=["email_verified", "verification_token"])

    # Activate the account after successful email verification.
    User.objects.filter(pk=profile.user_id).update(is_active=True)

    return render(
        request,
        "events/verification_result.html",
        {
            "success": True,
            "message": "Your email has been verified successfully!",
        },
    )
def login_view(request):
    if request.method == "POST":
        form = GatherLoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Welcome back!")
            return redirect("register")
    else:
        form = GatherLoginForm(request)

    return render(request, "events/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")
