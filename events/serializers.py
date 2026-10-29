from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.models import User
from .models import Event, Registration, TicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)

    class Meta:
        model = TicketType
        fields = [
            "id",
            "name",
            "price",
            "quantity_limit",
            "sold_count",
            "available_quantity",
            "is_sold_out",
        ]
        read_only_fields = ["id", "sold_count", "available_quantity", "is_sold_out"]

    def validate_quantity_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity limit must be at least 1.")
        return value

    def validate_price(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Price cannot be negative.")
        return value


class EventSerializer(serializers.ModelSerializer):
    ticket_types = TicketTypeSerializer(many=True, read_only=True)
    organizer = serializers.ReadOnlyField(source="organizer.username")
    remaining_capacity = serializers.IntegerField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)
    is_published = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "organizer",
            "title",
            "name",
            "description",
            "category",
            "venue",
            "date",
            "ticket_price",
            "capacity",
            "status",
            "is_published",
            "remaining_capacity",
            "is_sold_out",
            "ticket_types",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organizer",
            "status",
            "is_published",
            "remaining_capacity",
            "is_sold_out",
            "ticket_types",
            "created_at",
            "updated_at",
        ]

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than zero.")
        return value

    def validate_ticket_price(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Ticket price cannot be negative.")
        return value


class RegistrationSerializer(serializers.ModelSerializer):
    ticket_type_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Registration
        fields = [
            "id",
            "event",
            "ticket_type",
            "ticket_type_id",
            "quantity",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "event", "ticket_type", "status", "created_at"]


class UserAdminSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False)
    email_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "is_active",
            "email_verified",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "date_joined",
            "last_login",
            "email_verified",
        ]

    def get_email_verified(self, obj):
        profile = getattr(obj, "profile", None)
        return bool(profile and profile.email_verified)

    def validate_role(self, value):
        try:
            from accounts.roles import Role
        except ImportError:
            from RBAC.accounts.roles import Role

        if value not in Role.values:
            raise serializers.ValidationError(
                f"Invalid role. Choices are: {list(Role.values)}"
            )
        return value

    def update(self, instance, validated_data):
        if "role" in validated_data:
            instance.role = validated_data["role"]
        if "is_active" in validated_data:
            instance.is_active = validated_data["is_active"]
            instance.save(update_fields=["is_active"])
        return instance
