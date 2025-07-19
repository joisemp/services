from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.contenttypes.models import ContentType
from .models import FinancialTransaction, Budget, TransactionCategory


def calculate_monthly_summary(org, year=None, month=None):
    """Calculate monthly financial summary for an organization"""
    if not year:
        year = timezone.now().year
    if not month:
        month = timezone.now().month
    
    # Create date range for the month
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()
    
    transactions = FinancialTransaction.objects.filter(
        org=org,
        transaction_date__gte=start_date,
        transaction_date__lt=end_date,
        status='completed'
    )
    
    # Calculate totals
    income = transactions.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    expenses = transactions.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Category breakdown
    expense_categories = transactions.filter(
        transaction_type='expense'
    ).values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    income_categories = transactions.filter(
        transaction_type='income'
    ).values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    return {
        'period': f"{start_date.strftime('%B %Y')}",
        'income': income,
        'expenses': expenses,
        'net_income': income - expenses,
        'transaction_count': transactions.count(),
        'expense_categories': list(expense_categories),
        'income_categories': list(income_categories),
        'start_date': start_date,
        'end_date': end_date,
    }


def calculate_yearly_summary(org, year=None):
    """Calculate yearly financial summary for an organization"""
    if not year:
        year = timezone.now().year
    
    start_date = datetime(year, 1, 1).date()
    end_date = datetime(year + 1, 1, 1).date()
    
    transactions = FinancialTransaction.objects.filter(
        org=org,
        transaction_date__gte=start_date,
        transaction_date__lt=end_date,
        status='completed'
    )
    
    # Calculate totals
    income = transactions.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    expenses = transactions.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Monthly breakdown
    monthly_data = []
    for month in range(1, 13):
        month_start = datetime(year, month, 1).date()
        if month == 12:
            month_end = datetime(year + 1, 1, 1).date()
        else:
            month_end = datetime(year, month + 1, 1).date()
        
        month_transactions = transactions.filter(
            transaction_date__gte=month_start,
            transaction_date__lt=month_end
        )
        
        month_income = month_transactions.filter(
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        month_expenses = month_transactions.filter(
            transaction_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        monthly_data.append({
            'month': month,
            'month_name': month_start.strftime('%B'),
            'income': month_income,
            'expenses': month_expenses,
            'net': month_income - month_expenses,
            'transaction_count': month_transactions.count()
        })
    
    return {
        'year': year,
        'income': income,
        'expenses': expenses,
        'net_income': income - expenses,
        'transaction_count': transactions.count(),
        'monthly_data': monthly_data,
        'start_date': start_date,
        'end_date': end_date,
    }


def calculate_budget_performance(org, start_date=None, end_date=None):
    """Calculate budget performance for an organization"""
    if not start_date:
        start_date = timezone.now().date().replace(day=1)
    if not end_date:
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
    
    # Get active budgets for the period
    budgets = Budget.objects.filter(
        org=org,
        is_active=True,
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    
    budget_performance = []
    total_budgeted = Decimal('0.00')
    total_spent = Decimal('0.00')
    
    for budget in budgets:
        spent = budget.get_spent_amount()
        remaining = budget.get_remaining_amount()
        percentage = budget.get_percentage_used()
        
        budget_performance.append({
            'budget': budget,
            'budgeted': budget.budgeted_amount,
            'spent': spent,
            'remaining': remaining,
            'percentage': percentage,
            'is_over': budget.is_over_budget(),
            'status': 'over' if budget.is_over_budget() else 'warning' if percentage > 80 else 'good'
        })
        
        total_budgeted += budget.budgeted_amount
        total_spent += spent
    
    return {
        'period': f"{start_date} to {end_date}",
        'budgets': budget_performance,
        'total_budgeted': total_budgeted,
        'total_spent': total_spent,
        'total_remaining': total_budgeted - total_spent,
        'overall_percentage': (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0,
        'start_date': start_date,
        'end_date': end_date,
    }


def get_expense_trends(org, months=6):
    """Get expense trends over the last N months"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=months * 30)
    
    trends = []
    current_date = start_date.replace(day=1)
    
    while current_date <= end_date:
        # Calculate next month
        if current_date.month == 12:
            next_month = current_date.replace(year=current_date.year + 1, month=1)
        else:
            next_month = current_date.replace(month=current_date.month + 1)
        
        # Get transactions for this month
        month_transactions = FinancialTransaction.objects.filter(
            org=org,
            transaction_date__gte=current_date,
            transaction_date__lt=next_month,
            status='completed'
        )
        
        month_income = month_transactions.filter(
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        month_expenses = month_transactions.filter(
            transaction_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        trends.append({
            'date': current_date,
            'month': current_date.strftime('%B %Y'),
            'income': month_income,
            'expenses': month_expenses,
            'net': month_income - month_expenses,
            'transaction_count': month_transactions.count()
        })
        
        current_date = next_month
    
    return trends


def get_top_categories(org, start_date=None, end_date=None, limit=5):
    """Get top spending categories"""
    if not start_date:
        start_date = timezone.now().date().replace(day=1)
    if not end_date:
        end_date = timezone.now().date()
    
    categories = FinancialTransaction.objects.filter(
        org=org,
        transaction_type='expense',
        status='completed',
        transaction_date__gte=start_date,
        transaction_date__lte=end_date
    ).values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:limit]
    
    return list(categories)


def link_transaction_to_object(transaction, related_object):
    """Link a transaction to another model object"""
    content_type = ContentType.objects.get_for_model(related_object)
    transaction.content_type = content_type
    transaction.object_id = related_object.id
    transaction.save()


def create_transaction_from_object(obj, amount, transaction_type, title=None, description=None, category=None, user=None):
    """Create a transaction linked to another model object"""
    from .models import FinancialTransaction
    
    # Get organization from the object if possible
    org = None
    if hasattr(obj, 'org'):
        org = obj.org
    elif hasattr(obj, 'organisation'):
        org = obj.organisation
    elif user and hasattr(user, 'profile'):
        org = user.profile.org
    
    if not org:
        raise ValueError("Could not determine organization for transaction")
    
    # Generate title if not provided
    if not title:
        title = f"{transaction_type.title()} for {obj.__class__.__name__} #{obj.id}"
    
    # Create transaction
    transaction = FinancialTransaction.objects.create(
        title=title,
        description=description or f"Auto-generated transaction for {obj}",
        amount=amount,
        transaction_type=transaction_type,
        org=org,
        category=category,
        created_by=user,
        status='completed'
    )
    
    # Link to object
    link_transaction_to_object(transaction, obj)
    
    return transaction


def calculate_cash_flow(org, start_date=None, end_date=None):
    """Calculate cash flow for a period"""
    if not start_date:
        start_date = timezone.now().date().replace(day=1)
    if not end_date:
        end_date = timezone.now().date()
    
    transactions = FinancialTransaction.objects.filter(
        org=org,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
        status='completed'
    )
    
    # Calculate cash inflows
    inflows = transactions.filter(
        transaction_type__in=['income', 'refund']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Calculate cash outflows
    outflows = transactions.filter(
        transaction_type__in=['expense', 'transfer']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Daily cash flow
    daily_flow = []
    current_date = start_date
    
    while current_date <= end_date:
        day_transactions = transactions.filter(transaction_date__date=current_date)
        
        day_inflows = day_transactions.filter(
            transaction_type__in=['income', 'refund']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        day_outflows = day_transactions.filter(
            transaction_type__in=['expense', 'transfer']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        daily_flow.append({
            'date': current_date,
            'inflows': day_inflows,
            'outflows': day_outflows,
            'net_flow': day_inflows - day_outflows
        })
        
        current_date += timedelta(days=1)
    
    return {
        'period': f"{start_date} to {end_date}",
        'total_inflows': inflows,
        'total_outflows': outflows,
        'net_cash_flow': inflows - outflows,
        'daily_flow': daily_flow,
        'start_date': start_date,
        'end_date': end_date,
    }


def get_financial_health_score(org):
    """Calculate a financial health score (0-100)"""
    # Get current month data
    current_month = timezone.now().replace(day=1)
    next_month = (current_month + timedelta(days=32)).replace(day=1)
    
    # Get last 3 months data
    three_months_ago = current_month - timedelta(days=90)
    
    transactions = FinancialTransaction.objects.filter(
        org=org,
        transaction_date__gte=three_months_ago,
        transaction_date__lt=next_month,
        status='completed'
    )
    
    # Calculate metrics
    total_income = transactions.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    total_expenses = transactions.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Score components
    score = 0
    
    # 1. Positive cash flow (40 points)
    if total_income > total_expenses:
        score += 40
    elif total_income > total_expenses * Decimal('0.8'):
        score += 20
    
    # 2. Budget compliance (30 points)
    active_budgets = Budget.objects.filter(
        org=org,
        is_active=True,
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    )
    
    if active_budgets.exists():
        over_budget_count = sum(1 for budget in active_budgets if budget.is_over_budget())
        budget_compliance = 1 - (over_budget_count / active_budgets.count())
        score += int(budget_compliance * 30)
    else:
        score += 15  # Some points for having no budgets (better than being over budget)
    
    # 3. Transaction regularity (20 points)
    transaction_count = transactions.count()
    if transaction_count > 30:  # More than 10 transactions per month
        score += 20
    elif transaction_count > 15:
        score += 10
    elif transaction_count > 5:
        score += 5
    
    # 4. Expense diversity (10 points)
    expense_categories = transactions.filter(
        transaction_type='expense'
    ).values('category').distinct().count()
    
    if expense_categories > 5:
        score += 10
    elif expense_categories > 3:
        score += 5
    elif expense_categories > 1:
        score += 2
    
    return min(score, 100)  # Cap at 100


def get_category_insights(org, start_date=None, end_date=None):
    """Get insights about spending patterns by category"""
    if not start_date:
        start_date = timezone.now().date().replace(day=1)
    if not end_date:
        end_date = timezone.now().date()
    
    # Get category spending
    categories = TransactionCategory.objects.filter(org=org, is_active=True)
    category_insights = []
    
    for category in categories:
        transactions = FinancialTransaction.objects.filter(
            org=org,
            category=category,
            transaction_date__gte=start_date,
            transaction_date__lte=end_date,
            status='completed'
        )
        
        income = transactions.filter(transaction_type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        expenses = transactions.filter(transaction_type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Calculate average transaction size
        avg_transaction = transactions.aggregate(avg=Sum('amount'))['avg'] or Decimal('0.00')
        if transactions.count() > 0:
            avg_transaction = transactions.aggregate(total=Sum('amount'))['total'] / transactions.count()
        
        category_insights.append({
            'category': category,
            'income': income,
            'expenses': expenses,
            'net': income - expenses,
            'transaction_count': transactions.count(),
            'avg_transaction': avg_transaction,
            'percentage_of_total': 0  # Will be calculated below
        })
    
    # Calculate percentages
    total_expenses = sum(insight['expenses'] for insight in category_insights)
    if total_expenses > 0:
        for insight in category_insights:
            insight['percentage_of_total'] = (insight['expenses'] / total_expenses) * 100
    
    # Sort by expense amount
    category_insights.sort(key=lambda x: x['expenses'], reverse=True)
    
    return category_insights
