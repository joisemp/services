# Data migration to populate issue_id for existing issues
from django.db import migrations
import random
import string


def populate_issue_ids(apps, schema_editor):
    """Populate issue_id for all existing issues"""
    Issue = apps.get_model('issue_management', 'Issue')
    
    for issue in Issue.objects.filter(issue_id__isnull=True):
        # Generate issue_id with org prefix
        org_prefix = issue.org.name[:3].upper() if issue.org else 'ISS'
        
        # Generate unique code
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            issue_id_candidate = f"{org_prefix}-{code}"
            if not Issue.objects.filter(issue_id=issue_id_candidate).exists():
                issue.issue_id = issue_id_candidate
                issue.save(update_fields=['issue_id'])
                break


def reverse_populate_issue_ids(apps, schema_editor):
    """Reverse migration - set issue_id to None"""
    Issue = apps.get_model('issue_management', 'Issue')
    Issue.objects.all().update(issue_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('issue_management', '0023_issue_issue_id'),
        ('core', '0001_initial'),  # Ensure Organization model is available
    ]

    operations = [
        migrations.RunPython(populate_issue_ids, reverse_populate_issue_ids),
    ]
