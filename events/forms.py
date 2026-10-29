from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from .models import Event, TicketType


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        validators=[validate_password],
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Choose a username"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


class GatherLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(
            attrs={"placeholder": "Enter your username"}
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Enter your password"}
        ),
    )


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "category",
            "venue",
            "date",
            "capacity",
            "ticket_price",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Tech Innovations Summit 2026",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Detailed description of the event...",
                }
            ),
            "category": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Technology, Business, Workshop",
                }
            ),
            "venue": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Bangalore International Exhibition Centre",
                }
            ),
            "date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "capacity": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "ticket_price": forms.NumberInput(
                attrs={"class": "form-control", "min": "0.00", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.date:
            # Format datetime for HTML5 datetime-local input
            self.initial["date"] = self.instance.date.strftime("%Y-%m-%dT%H:%M")
        if self.instance and not self.initial.get("title") and getattr(self.instance, "name", None):
            self.initial["title"] = self.instance.name

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")
        if capacity is not None and capacity <= 0:
            raise forms.ValidationError("Capacity must be greater than zero.")
        return capacity

    def clean_ticket_price(self):
        ticket_price = self.cleaned_data.get("ticket_price")
        if ticket_price is not None and ticket_price < Decimal("0.00"):
            raise forms.ValidationError("Ticket price cannot be negative.")
        return ticket_price

    def clean_date(self):
        event_date = self.cleaned_data.get("date")
        if event_date and event_date <= timezone.now():
            raise forms.ValidationError("Event date must be in the future.")
        return event_date


class TicketTypeForm(forms.ModelForm):
    class Meta:
        model = TicketType
        fields = ["name", "price", "quantity_limit"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., VIP, Early Bird, General",
                }
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "min": "0.00", "step": "0.01"}
            ),
            "quantity_limit": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
        }

    def clean_quantity_limit(self):
        limit = self.cleaned_data.get("quantity_limit")
        if limit is not None and limit <= 0:
            raise forms.ValidationError("Quantity limit must be at least 1.")
        return limit

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < Decimal("0.00"):
            raise forms.ValidationError("Price cannot be negative.")
        return price


class EventRegistrationForm(forms.Form):
    ticket_type = forms.ModelChoiceField(
        queryset=TicketType.objects.none(),
        required=False,
        empty_label="General Admission",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
    )

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        if event is not None:
            self.event = event
            self.fields["ticket_type"].queryset = event.ticket_types.all()
