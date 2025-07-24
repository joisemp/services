#!/usr/bin/env python
"""
Script to populate sample data for testing the dashboard functionality.
Run this with: python manage.py shell < populate_dashboard_data.py
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User, UserProfile, Organisation
from service_management.models import Spaces, WorkCategory
from issue_management.models import Issue, IssueCategory
from finance.models import FinancialTransaction, TransactionCategory

def create_sample_data():
    """Create sample data for dashboard testing"""
    
    # Create or get an organization
    org, created = Organisation.objects.get_or_create(
        name="Tech Solutions Inc.",
        defaults={
            'address': "123 Tech Street, Innovation City",
            'currency_code': 'USD'
        }
    )
    print(f"Organization: {org.name} ({'created' if created else 'exists'})")
    
    # Create central admin user
    admin_user, created = User.objects.get_or_create(
        email="admin@techsolutions.com",
        defaults={'is_staff': True, 'is_superuser': True}
    )
    if created:
        admin_user.set_password("admin123")
        admin_user.save()
    
    admin_profile, created = UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={
            'first_name': 'John',
            'last_name': 'Admin',
            'user_type': 'central_admin',
            'org': org
        }
    )
    print(f"Central Admin: {admin_profile} ({'created' if created else 'exists'})")
    
    # Create space admin user
    space_admin_user, created = User.objects.get_or_create(
        email="spaceadmin@techsolutions.com"
    )
    if created:
        space_admin_user.set_password("space123")
        space_admin_user.save()
    
    space_admin_profile, created = UserProfile.objects.get_or_create(
        user=space_admin_user,
        defaults={
            'first_name': 'Jane',
            'last_name': 'SpaceAdmin',
            'user_type': 'space_admin',
            'org': org
        }
    )
    print(f"Space Admin: {space_admin_profile} ({'created' if created else 'exists'})")
    
    # Create general users
    general_users = []
    for i in range(3):
        user, created = User.objects.get_or_create(
            email=f"user{i+1}@techsolutions.com"
        )
        if created:
            user.set_password("user123")
            user.save()
        
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'first_name': f'User{i+1}',
                'last_name': 'TestUser',
                'user_type': 'general_user',
                'org': org
            }
        )
        general_users.append(profile)
        print(f"General User: {profile} ({'created' if created else 'exists'})")
    
    # Create maintainer user
    maintainer_user, created = User.objects.get_or_create(
        email="maintainer@techsolutions.com"
    )
    if created:
        maintainer_user.set_password("maintainer123")
        maintainer_user.save()
    
    maintainer_profile, created = UserProfile.objects.get_or_create(
        user=maintainer_user,
        defaults={
            'first_name': 'Mike',
            'last_name': 'Maintainer',
            'user_type': 'maintainer',
            'org': org
        }
    )
    print(f"Maintainer: {maintainer_profile} ({'created' if created else 'exists'})")
    
    # Create spaces
    spaces = []
    space_names = ["Main Office", "Remote Hub", "Development Lab"]
    for name in space_names:
        space, created = Spaces.objects.get_or_create(
            name=name,
            org=org,
            defaults={
                'description': f'Description for {name}',
                'created_by': admin_user,
                'is_access_enabled': True,
                'require_approval': False
            }
        )
        space.space_admins.add(space_admin_user)
        spaces.append(space)
        print(f"Space: {space} ({'created' if created else 'exists'})")
    
    # Set current active space for space admin
    space_admin_profile.current_active_space = spaces[0]
    space_admin_profile.save()
    
    # Create work categories
    categories = ['IT Support', 'Maintenance', 'Cleaning', 'Security']
    for cat_name in categories:
        category, created = WorkCategory.objects.get_or_create(
            name=cat_name,
            org=org,
            defaults={'description': f'{cat_name} related work'}
        )
        print(f"Work Category: {category} ({'created' if created else 'exists'})")
    
    # Create issue categories
    issue_categories = []
    issue_cat_names = ['Hardware Issue', 'Software Bug', 'Network Problem', 'Facility Issue']
    for cat_name in issue_cat_names:
        category, created = IssueCategory.objects.get_or_create(
            name=cat_name,
            org=org,
            defaults={'description': f'{cat_name} category'}
        )
        issue_categories.append(category)
        print(f"Issue Category: {category} ({'created' if created else 'exists'})")
    
    # Create sample issues with various statuses and dates
    statuses = ['open', 'in_progress', 'resolved', 'closed', 'escalated']
    priorities = ['low', 'medium', 'high', 'critical']
    
    # Create issues from the last 6 months
    for i in range(30):  # Create 30 issues
        # Distribute issues across the last 6 months
        days_ago = i * 6  # Spread over ~180 days
        created_date = timezone.now() - timedelta(days=days_ago)
        
        issue, created = Issue.objects.get_or_create(
            title=f"Sample Issue #{i+1}",
            defaults={
                'description': f'This is a sample issue created for testing dashboard functionality. Issue #{i+1}',
                'status': statuses[i % len(statuses)],
                'priority': priorities[i % len(priorities)],
                'category': issue_categories[i % len(issue_categories)],
                'org': org,
                'space': spaces[i % len(spaces)],
                'created_by': general_users[i % len(general_users)].user,
                'maintainer': maintainer_user if i % 3 == 0 else None,
                'created_at': created_date,
                'updated_at': created_date
            }
        )
        
        if created:
            # Update the created_at time manually since auto_now_add doesn't allow it
            Issue.objects.filter(id=issue.id).update(
                created_at=created_date,
                updated_at=created_date
            )
        
        print(f"Issue: {issue.title} ({'created' if created else 'exists'})")
    
    # Create transaction categories
    trans_categories = []
    trans_cat_names = ['Office Supplies', 'Equipment', 'Utilities', 'Maintenance']
    for cat_name in trans_cat_names:
        category, created = TransactionCategory.objects.get_or_create(
            name=cat_name,
            org=org,
            defaults={'description': f'{cat_name} expenses'}
        )
        trans_categories.append(category)
        print(f"Transaction Category: {category} ({'created' if created else 'exists'})")
    
    # Create sample transactions
    transaction_types = ['expense', 'income']
    payment_methods = ['cash', 'bank_transfer', 'credit_card']
    
    for i in range(15):  # Create 15 transactions
        days_ago = i * 12  # Spread over ~180 days
        trans_date = timezone.now() - timedelta(days=days_ago)
        
        transaction, created = FinancialTransaction.objects.get_or_create(
            title=f"Sample Transaction #{i+1}",
            defaults={
                'description': f'Sample transaction for testing dashboard',
                'amount': 100 + (i * 50),  # Amounts from 100 to 800
                'transaction_type': transaction_types[i % len(transaction_types)],
                'payment_method': payment_methods[i % len(payment_methods)],
                'status': 'completed',
                'category': trans_categories[i % len(trans_categories)],
                'org': org,
                'space': spaces[i % len(spaces)],
                'created_by': admin_user,
                'transaction_date': trans_date
            }
        )
        
        if created:
            FinancialTransaction.objects.filter(id=transaction.id).update(
                created_at=trans_date,
                transaction_date=trans_date
            )
        
        print(f"Transaction: {transaction.title} ({'created' if created else 'exists'})")
    
    print("\n" + "="*50)
    print("Sample data creation completed!")
    print("="*50)
    print(f"Organization: {org.name}")
    print(f"Users created: Central Admin, Space Admin, 3 General Users, 1 Maintainer")
    print(f"Spaces created: {len(spaces)}")
    print(f"Issues created: 30 with various statuses across 6 months")
    print(f"Transactions created: 15 across 6 months")
    print("\nTest login credentials:")
    print("Central Admin: admin@techsolutions.com / admin123")
    print("Space Admin: spaceadmin@techsolutions.com / space123")
    print("General User: user1@techsolutions.com / user123")
    print("Maintainer: maintainer@techsolutions.com / maintainer123")
    print("="*50)

if __name__ == "__main__":
    create_sample_data()
