from django.db import migrations


INDEXES = {
    "event_title_trgm_idx": "title",
    "event_name_trgm_idx": "name",
    "event_description_trgm_idx": "description",
    "event_venue_trgm_idx": "venue",
}


def add_postgres_search_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        for index_name, column in INDEXES.items():
            cursor.execute(
                f'CREATE INDEX "{index_name}" ON "events_event" '
                f'USING gin ((UPPER("{column}")) gin_trgm_ops)'
            )


def remove_postgres_search_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for index_name in reversed(INDEXES):
            cursor.execute(f'DROP INDEX IF EXISTS "{index_name}"')


class Migration(migrations.Migration):
    dependencies = [("events", "0005_nonfunctional_foundations")]

    operations = [
        migrations.RunPython(
            add_postgres_search_indexes,
            remove_postgres_search_indexes,
        ),
    ]
