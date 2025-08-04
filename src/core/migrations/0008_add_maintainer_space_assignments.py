# Generated manually - Add maintainer space assignments

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_userprofile_current_active_space_and_more'),
        ('service_management', '0013_remove_spacesettings_enable_dashboard'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='assigned_spaces',
            field=models.ManyToManyField(
                blank=True,
                help_text='Spaces this maintainer is assigned to. Leave empty for organization-wide availability.',
                limit_choices_to={'org': models.F('org')},
                related_name='assigned_maintainers',
                to='service_management.spaces'
            ),
        ),
    ]
