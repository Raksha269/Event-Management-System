"""Verify staging seeds cannot silently modify unrelated databases or datasets."""
from io import StringIO
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase

from events.models import Event, TicketType


class StagingSeedTests(TestCase):
    def test_requires_explicit_environment_opt_in(self):
        with patch.dict("os.environ", {"EMS_ISOLATED_STAGING": ""}):
            with self.assertRaises(CommandError):
                call_command("seed_postgres_staging")
        self.assertEqual(Event.objects.count(), 0)

    def test_rejects_non_staging_database(self):
        with patch.dict("os.environ", {"EMS_ISOLATED_STAGING": "synthetic-only"}):
            with self.assertRaises(CommandError):
                call_command("seed_postgres_staging")
        self.assertEqual(Event.objects.count(), 0)

    def staging_config(self):
        return patch.dict(connection.settings_dict, {"NAME": "ems_staging", "HOST": "127.0.0.1"})

    def test_rejects_sqlite_even_with_staging_name(self):
        with self.staging_config(), patch.object(connection, "vendor", "sqlite"), patch.dict(
                "os.environ", {"EMS_ISOLATED_STAGING": "synthetic-only"}):
            with self.assertRaises(CommandError):
                call_command("seed_postgres_staging")

    def test_rejects_existing_users_without_changing_them(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL seed guard")
        get_user_model().objects.create_user(username="existing")
        with self.staging_config(), patch.dict("os.environ", {"EMS_ISOLATED_STAGING": "synthetic-only"}):
            with self.assertRaises(CommandError):
                call_command("seed_postgres_staging")
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(Event.objects.count(), 0)

    def test_exact_dataset_and_second_run_refusal(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL seed integration")
        output = StringIO()
        with self.staging_config(), patch.dict("os.environ", {"EMS_ISOLATED_STAGING": "synthetic-only"}):
            call_command("seed_postgres_staging", stdout=output)
            self.assertEqual(json.loads(output.getvalue()), {
                "events": 1500, "published": 1233, "published_sample_matches": 233, "ticket_types": 3000})
            with self.assertRaises(CommandError):
                call_command("seed_postgres_staging")
        self.assertEqual(Event.objects.count(), 1500)
        self.assertEqual(TicketType.objects.count(), 3000)
        self.assertFalse(get_user_model().objects.get(username="staging_organizer").has_usable_password())
