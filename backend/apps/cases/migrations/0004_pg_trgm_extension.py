# Ensures the pg_trgm extension exists for trigram similarity search
# (spec §25/§67). Idempotent; PostgreSQL only.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0003_caseevent_caselawyer_caseparty_casestatushistory_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS pg_trgm;',
            reverse_sql='DROP EXTENSION IF EXISTS pg_trgm;',
        ),
    ]
