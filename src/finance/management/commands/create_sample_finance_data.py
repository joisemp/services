from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random

from finance.models import (
    TransactionCategory,
    FinancialTransaction,
    RecurringTransaction,
    Budget
)
from core.models import Organisation, User


class Command(BaseCommand):
    help = 'Create sample financial data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-id',
            type=int,
            help='Organization ID to create data for (default: first organization)',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of transactions to create (default: 50)',
        )

    def handle(self, *args, **options):
        org_id = options.get('org_id')
        count = options.get('count', 50)
        
        # Get organization
        if org_id:
            try:
                org = Organisation.objects.get(id=org_id)
            except Organisation.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Organization with ID {org_id} not found'))
                return
        else:
            org = Organisation.objects.first()
            if not org:
                self.stdout.write(self.style.ERROR('No organizations found'))
                return
        
        # Get a user for the organization
        user = User.objects.filter(profile__org=org).first()
        if not user:
            self.stdout.write(self.style.ERROR(f'No users found for organization {org.name}'))
            return
        
        self.stdout.write(f'Creating sample data for organization: {org.name}')
        
        # Create categories
        categories_data = [
            ('Office Supplies', 'Office supplies and equipment'),
            ('Utilities', 'Electricity, water, internet, and other utilities'),
            ('Transportation', 'Vehicle fuel, maintenance, and transportation costs'),
            ('Food & Catering', 'Meals, catering, and food expenses'),
            ('Maintenance', 'Building and equipment maintenance'),
            ('Marketing', 'Marketing and advertising expenses'),
            ('Professional Services', 'Legal, accounting, and consulting services'),
            ('Insurance', 'Various insurance premiums'),
            ('Training', 'Employee training and development'),
            ('Technology', 'Software, hardware, and IT services'),
            ('Service Revenue', 'Revenue from services provided'),
            ('Product Sales', 'Revenue from product sales'),
            ('Consulting', 'Consulting and advisory income'),
            ('Grants', 'Grant money received'),
            ('Donations', 'Donations and contributions received'),
        ]
        
        categories = []
        for name, description in categories_data:
            category, created = TransactionCategory.objects.get_or_create(
                name=name,
                org=org,
                defaults={'description': description}
            )
            categories.append(category)
            if created:
                self.stdout.write(f'Created category: {name}')
        
        # Create sample transactions
        transaction_types = ['income', 'expense']
        payment_methods = ['cash', 'bank_transfer', 'credit_card', 'debit_card', 'check']
        statuses = ['completed', 'pending', 'completed', 'completed']  # Bias towards completed
        
        # Sample transaction titles
        expense_titles = [
            'Office supply purchase',
            'Electricity bill payment',
            'Fuel for company vehicle',
            'Team lunch meeting',
            'Equipment maintenance',
            'Internet service payment',
            'Building rent',
            'Insurance premium',
            'Software subscription',
            'Conference registration',
            'Marketing materials',
            'Legal consultation',
            'Equipment repair',
            'Training workshop',
            'Cleaning services',
        ]
        
        income_titles = [
            'Service contract payment',
            'Product sales revenue',
            'Consulting project',
            'Grant funding',
            'Donation received',
            'Training workshop fee',
            'Maintenance service',
            'Software licensing',
            'Equipment rental',
            'Advisory services',
        ]
        
        transactions_created = 0
        
        for i in range(count):
            # Random transaction type
            transaction_type = random.choice(transaction_types)
            
            # Select appropriate title and category
            if transaction_type == 'expense':
                title = random.choice(expense_titles)
                # Select from expense categories (first 10)
                category = random.choice(categories[:10])
                amount = Decimal(str(random.uniform(10, 5000)))
            else:
                title = random.choice(income_titles)
                # Select from income categories (last 5)
                category = random.choice(categories[10:])
                amount = Decimal(str(random.uniform(100, 10000)))
            
            # Random date within last 6 months
            days_ago = random.randint(0, 180)
            transaction_date = timezone.now() - timedelta(days=days_ago)
            
            # Create transaction
            transaction = FinancialTransaction.objects.create(
                title=title,
                description=f'Sample {transaction_type} transaction for {title.lower()}',
                amount=amount.quantize(Decimal('0.01')),
                transaction_type=transaction_type,
                payment_method=random.choice(payment_methods),
                status=random.choice(statuses),
                category=category,
                org=org,
                created_by=user,
                transaction_date=transaction_date,
                reference_number=f'REF{random.randint(10000, 99999)}',
            )
            
            transactions_created += 1
            
            if transactions_created % 10 == 0:
                self.stdout.write(f'Created {transactions_created} transactions...')
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {transactions_created} transactions')
        )
        
        # Create sample recurring transactions
        recurring_data = [
            ('Monthly Office Rent', 'expense', 2500.00, 'monthly', 'Office Supplies'),
            ('Internet Service', 'expense', 150.00, 'monthly', 'Utilities'),
            ('Insurance Premium', 'expense', 500.00, 'monthly', 'Insurance'),
            ('Monthly Service Contract', 'income', 5000.00, 'monthly', 'Service Revenue'),
            ('Software Subscription', 'expense', 200.00, 'monthly', 'Technology'),
            ('Quarterly Marketing Budget', 'expense', 1500.00, 'quarterly', 'Marketing'),
            ('Annual Equipment Maintenance', 'expense', 3000.00, 'yearly', 'Maintenance'),
        ]
        
        recurring_created = 0
        
        for title, transaction_type, amount, frequency, category_name in recurring_data:
            # Find category
            category = next((cat for cat in categories if cat.name == category_name), None)
            
            # Random start date (within last month)
            start_date = (timezone.now() - timedelta(days=random.randint(1, 30))).date()
            
            recurring = RecurringTransaction.objects.create(
                title=title,
                description=f'Recurring {transaction_type} for {title.lower()}',
                amount=Decimal(str(amount)),
                frequency=frequency,
                start_date=start_date,
                next_due_date=start_date,
                transaction_type=transaction_type,
                payment_method='bank_transfer',
                category=category,
                org=org,
                created_by=user,
                is_active=True,
                auto_create=True,
            )
            
            recurring_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {recurring_created} recurring transactions')
        )
        
        # Create sample budgets
        budget_data = [
            ('Monthly Office Expenses', 'monthly', 5000.00, 'Office Supplies'),
            ('Quarterly Marketing', 'quarterly', 4500.00, 'Marketing'),
            ('Annual Technology Budget', 'yearly', 15000.00, 'Technology'),
            ('Monthly Utilities', 'monthly', 1000.00, 'Utilities'),
            ('Overall Monthly Budget', 'monthly', 15000.00, None),  # Overall budget
        ]
        
        budgets_created = 0
        
        for name, period, amount, category_name in budget_data:
            # Find category
            category = None
            if category_name:
                category = next((cat for cat in categories if cat.name == category_name), None)
            
            # Set date range based on period
            start_date = timezone.now().date().replace(day=1)
            
            if period == 'monthly':
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
                end_date = end_date - timedelta(days=1)
            elif period == 'quarterly':
                end_date = start_date + timedelta(days=90)
            else:  # yearly
                end_date = start_date.replace(year=start_date.year + 1) - timedelta(days=1)
            
            budget = Budget.objects.create(
                name=name,
                description=f'{period.title()} budget for {name.lower()}',
                category=category,
                budgeted_amount=Decimal(str(amount)),
                period=period,
                start_date=start_date,
                end_date=end_date,
                org=org,
                created_by=user,
                is_active=True,
            )
            
            budgets_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {budgets_created} budgets')
        )
        
        # Final summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSample data creation complete!\n'
                f'Organization: {org.name}\n'
                f'Categories: {len(categories)}\n'
                f'Transactions: {transactions_created}\n'
                f'Recurring Transactions: {recurring_created}\n'
                f'Budgets: {budgets_created}'
            )
        )
