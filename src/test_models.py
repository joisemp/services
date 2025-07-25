#!/usr/bin/env python
import os
import sys
import django

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    
    try:
        from issue_management.models import Issue, IssueCategory, IssueComment, IssueStatusHistory
        print("✓ All models imported successfully")
        
        # Check if we can run makemigrations
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'makemigrations', 'issue_management'])
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
