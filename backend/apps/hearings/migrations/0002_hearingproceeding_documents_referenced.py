# Generated manually: adds the documents_referenced M2M after both
# hearings.0001 and documents.0003 exist (breaks the circular dependency).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hearings', '0001_initial'),
        ('documents', '0003_documentaccess_documentchunk_casedocument_checksum_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='hearingproceeding',
            name='documents_referenced',
            field=models.ManyToManyField(
                blank=True,
                related_name='referenced_in_proceedings',
                to='documents.casedocument',
            ),
        ),
    ]
