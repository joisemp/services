import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_user_allow_phone_login'),
        ('ticket_management', '0028_rename_issue_to_ticket'),
    ]

    operations = [
        migrations.RenameField(
            model_name='update',
            old_name='related_issue',
            new_name='related_ticket',
        ),
        migrations.AlterField(
            model_name='update',
            name='related_ticket',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='updates',
                to='ticket_management.ticket',
            ),
        ),
    ]
