"""Fixed synthetic search dataset for a deliberately isolated PostgreSQL database."""
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from events.models import Event, TicketType, UserProfile


class Command(BaseCommand):
    help = "Seed an empty ems_staging database; never modifies an existing dataset."

    def handle(self, *args, **options):
        config = connection.settings_dict
        if (connection.vendor != "postgresql"
                or config["NAME"] != "ems_staging"
                or config["HOST"] != "127.0.0.1"
                or os.environ.get("EMS_ISOLATED_STAGING") != "synthetic-only"):
            raise CommandError("Requires explicitly opted-in loopback PostgreSQL ems_staging.")
        if Event.objects.exists() or get_user_model().objects.exists():
            raise CommandError("Seed requires an empty event/user dataset; no data was changed.")
        categories = ["Technology", "Music", "Sports", "Education", "Art", "Business"]
        venues = ["Bengaluru Hall", "Mysuru Centre", "University Auditorium"]
        with transaction.atomic():
            organizer = get_user_model().objects.create_user(username="staging_organizer")
            organizer.set_unusable_password()
            organizer.save(update_fields=["password"])
            UserProfile.objects.update_or_create(user=organizer, defaults={"role": "organizer"})
            events = []
            for i in range(1500):
                title = f"{'Sample' if i < 233 else 'Community'} {categories[i % 6]} Event {i:04d}"
                status = (Event.Status.PUBLISHED if i < 1233 else
                          [Event.Status.DRAFT, Event.Status.UNPUBLISHED, Event.Status.CANCELLED][i % 3])
                events.append(Event(
                    organizer=organizer, name=title, title=title,
                    description=f"Synthetic fixture {i}; workshops, talks and activities.",
                    category=categories[i % 6], venue=venues[i % 3],
                    date=datetime(2030, 1, 1, tzinfo=timezone.utc) + timedelta(days=i % 365),
                    ticket_price=Decimal(i % 5) * 199, capacity=100 + i % 5 * 100,
                    status=status,
                ))
            Event.objects.bulk_create(events, batch_size=500)
            TicketType.objects.bulk_create([
                TicketType(event=event, name=name, price=event.ticket_price + extra,
                           quantity_limit=event.capacity // 2)
                for event in events
                for name, extra in [("General", Decimal(0)), ("VIP", Decimal(100))]
            ], batch_size=500)
        self.stdout.write(json.dumps({
            "events": Event.objects.count(),
            "published": Event.objects.filter(status=Event.Status.PUBLISHED).count(),
            "published_sample_matches": Event.objects.filter(
                status=Event.Status.PUBLISHED, title__icontains="Sample").count(),
            "ticket_types": TicketType.objects.count(),
        }))
