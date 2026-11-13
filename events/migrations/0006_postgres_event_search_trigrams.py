from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import migrations
from django.db.models.functions import Upper


def add_postgres_search_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    event_model = apps.get_model("events", "Event")
    for index in _search_indexes():
        schema_editor.add_index(event_model, index)


def enable_trigram_extension(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def remove_postgres_search_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    event_model = apps.get_model("events", "Event")
    for index in reversed(_search_indexes()):
        schema_editor.remove_index(event_model, index)


def _search_indexes():
    return [
        GinIndex(
            OpClass(Upper("title"), name="gin_trgm_ops"),
            name="event_title_trgm_idx",
        ),
        GinIndex(
            OpClass(Upper("name"), name="gin_trgm_ops"),
            name="event_name_trgm_idx",
        ),
        GinIndex(
            OpClass(Upper("description"), name="gin_trgm_ops"),
            name="event_description_trgm_idx",
        ),
        GinIndex(
            OpClass(Upper("venue"), name="gin_trgm_ops"),
            name="event_venue_trgm_idx",
        ),
    ]


class Migration(migrations.Migration):
    dependencies = [("events", "0005_nonfunctional_foundations")]

    operations = [
        migrations.RunPython(enable_trigram_extension, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_postgres_search_indexes,
                    remove_postgres_search_indexes,
                )
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="event",
                    index=GinIndex(
                        OpClass(Upper("title"), name="gin_trgm_ops"),
                        name="event_title_trgm_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="event",
                    index=GinIndex(
                        OpClass(Upper("name"), name="gin_trgm_ops"),
                        name="event_name_trgm_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="event",
                    index=GinIndex(
                        OpClass(Upper("description"), name="gin_trgm_ops"),
                        name="event_description_trgm_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="event",
                    index=GinIndex(
                        OpClass(Upper("venue"), name="gin_trgm_ops"),
                        name="event_venue_trgm_idx",
                    ),
                ),
            ],
        ),
    ]
