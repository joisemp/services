import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from finance.models import Budget, FinancialTransaction

budget = Budget.objects.first()
print(f'Budget: {budget.name}')
print(f'Date range: {budget.start_date} to {budget.end_date}')
print(f'Budgeted amount: {budget.budgeted_amount}')
print(f'Spent amount: {budget.get_spent_amount()}')
print(f'Remaining: {budget.get_remaining_amount()}')
print(f'Percentage used: {budget.get_percentage_used()}%')
print()
print('All expense transactions:')
for t in FinancialTransaction.objects.filter(org=budget.org, transaction_type='expense'):
    print(f'- {t.description}: {t.amount} on {t.transaction_date.date()} (Category: {t.category}, Space: {t.space})')
