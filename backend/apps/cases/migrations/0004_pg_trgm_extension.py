# Ensures the pg_trgm extension exists for trigram similarity search
# (spec §25/§67). Idempotent; PostgreSQL only.

from django.db import migrations


def create_pg_trgm_extension(apps, schema_editor):
    """Install pg_trgm only on PostgreSQL; SQLite is used by the test suite."""
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')


def drop_pg_trgm_extension(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('DROP EXTENSION IF EXISTS pg_trgm;')


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0003_caseevent_caselawyer_caseparty_casestatushistory_and_more'),
    ]

    operations = [
        migrations.RunPython(create_pg_trgm_extension, drop_pg_trgm_extension),
    ]
