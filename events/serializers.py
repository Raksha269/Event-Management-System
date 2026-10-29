from decimal import Decimal

from rest_framework import serializers

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
