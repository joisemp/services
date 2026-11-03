from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fleet_management', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='vehicle',
            old_name='make',
            new_name='manufacturer',
        ),
    ]