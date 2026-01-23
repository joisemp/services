# Migration to make issue_id mandatory
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('issue_management', '0024_populate_issue_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issue',
            name='issue_id',
            field=models.CharField(max_length=20, unique=True, help_text='Unique identifier for the issue'),
        ),
    ]
