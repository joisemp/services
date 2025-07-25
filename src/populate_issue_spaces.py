#!/usr/bin/env python
"""
Simple script to populate existing issues with space information
Run this after adding the space field to Issue model
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from issue_management.models import Issue
from service_management.models import Spaces

def populate_issue_spaces():
    """Populate space field for existing issues"""
    issues_updated = 0
    
    # Get all issues without space assigned
    issues_without_space = Issue.objects.filter(space__isnull=True)
    
    print(f"Found {issues_without_space.count()} issues without space assignment")
    
    for issue in issues_without_space:
        if issue.org:
            # Try to find a space in the same organization
            first_space = Spaces.objects.filter(org=issue.org).first()
            if first_space:
                issue.space = first_space
                issue.save()
                issues_updated += 1
                print(f"Assigned issue '{issue.title}' to space '{first_space.name}'")
    
    print(f"Updated {issues_updated} issues with space information")

if __name__ == '__main__':
    populate_issue_spaces()
