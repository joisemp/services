from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_alter_user_user_type_add_driver'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='user_type',
            field=models.CharField(
                choices=[
                    ('central_admin', 'Central Admin'),
                    ('space_admin', 'Space Admin'),
                    ('maintainer', 'Maintainer'),
                    ('supervisor', 'Supervisor'),
                    ('reviewer', 'Reviewer'),
                    ('driver', 'Driver'),
                    ('transport_incharge', 'Transport Incharge'),
                    ('general_user', 'General User'),
                ],
                default='general_user',
                help_text='Role of the user in the system',
                max_length=20,
            ),
        ),
    ]
