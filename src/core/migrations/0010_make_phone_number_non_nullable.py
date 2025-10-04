# Generated manually on 2025-10-04

from django.core.validators import RegexValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_add_phone_numbers_to_existing_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone_number',
            field=models.CharField(
                help_text='Phone number is required for all users',
                max_length=17,
                unique=True,
                validators=[
                    RegexValidator(
                        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
                        regex='^\\+?1?\\d{9,15}$'
                    )
                ]
            ),
        ),
    ]
