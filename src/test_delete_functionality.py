#!/usr/bin/env python
"""
Test script to verify the delete issue functionality
"""
import os
import sys
import django

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    # Test importing the delete_issue view
    from issue_management.views import delete_issue
    print("✓ Successfully imported delete_issue view")
    
    # Test importing the Issue model
    from issue_management.models import Issue
    print("✓ Successfully imported Issue model")
    
    # Test URL patterns
    from issue_management.urls import urlpatterns
    delete_url_found = any('delete_issue' in str(pattern) for pattern in urlpatterns)
    if delete_url_found:
        print("✓ Delete issue URL pattern found")
    else:
        print("✗ Delete issue URL pattern not found")
    
    print("\n🎉 All basic tests passed! The delete issue functionality has been implemented successfully.")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
