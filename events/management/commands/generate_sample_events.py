
import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from events.models import Event


class Command(BaseCommand):
    help = "Generate synthetic events for local performance testing only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=500,
            help="Number of sample events to generate (default: 500).",
        )

    def handle(self, *args, **options):
        # Never run against production or a non-local database.
        if not settings.DEBUG:
            raise CommandError(
                "Sample data generation requires DEBUG=True."
            )

        if connection.vendor != "sqlite":
            raise CommandError(
                "Sample data generation is restricted to local SQLite."
            )

        database_name = str(settings.DATABASES["default"]["NAME"])
        from pathlib import Path

        database_path = Path(database_name).resolve()
        project_path = Path(settings.BASE_DIR).resolve()

        if project_path not in database_path.parents:
            raise CommandError(
                "Database must be located inside the local project folder."
            )

        count = options["count"]

        if count < 1 or count > 10000:
            raise CommandError(
                "Count must be between 1 and 10000."
            )

        categories = [
            "Technology",
            "Music",
            "Sports",
            "Education",
            "Business",
            "Art",
            "Food",
            "Health",
        ]

        venues = [
            "Bengaluru Convention Centre",
            "PES University",
            "Koramangala Auditorium",
            "Whitefield Tech Park",
            "Jayanagar Community Hall",
            "Electronic City",
            "Indiranagar Cultural Centre",
            "Mysuru Exhibition Grounds",
        ]

        statuses = [
            Event.Status.PUBLISHED,
            Event.Status.PUBLISHED,
            Event.Status.PUBLISHED,
            Event.Status.DRAFT,
            Event.Status.CANCELLED,
            Event.Status.UNPUBLISHED,
        ]

        rng = random.Random(42)
        now = timezone.now()
        events = []

        for i in range(1, count + 1):
            category = rng.choice(categories)
            venue = rng.choice(venues)
            status = rng.choice(statuses)

            event_date = now + timedelta(
                days=rng.randint(1, 365),
                hours=rng.randint(0, 23),
            )

            price = rng.choice([
                Decimal("0.00"),
                Decimal("199.00"),
                Decimal("499.00"),
                Decimal("999.00"),
                Decimal("1499.00"),
            ])

            title = f"Sample {category} Event {i}"

            events.append(
                Event(
                    name=title,
                    title=title,
                    description=(
                        f"Synthetic {category.lower()} event "
                        "created for local performance testing."
                    ),
                    category=category,
                    date=event_date,
                    venue=venue,
                    ticket_price=price,
                    capacity=rng.choice([1, 50, 100, 250, 500]),
                    status=status,
                )
            )

        with transaction.atomic():
            Event.objects.bulk_create(events, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {count} sample events."
            )
        )
