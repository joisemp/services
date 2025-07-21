from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from datetime import datetime, timedelta
import csv
import json
from decimal import Decimal

from .models import (
    TransactionCategory,
    FinancialTransaction,
    RecurringTransaction,
    Budget,
    TransactionAttachment,
    FinancialReport
)
from .forms import (
    TransactionCategoryForm,
    FinancialTransactionForm,
    RecurringTransactionForm,
    BudgetForm,
    TransactionAttachmentForm,
    FinancialReportForm,
    TransactionSearchForm,
    BulkTransactionForm
)
from .currency import get_template_currency_context

# Create your views here.

@login_required
def dashboard(request):
    """Main finance dashboard with overview stats"""
    user_org = request.user.profile.org
    
    # Get current month data
    current_month = timezone.now().replace(day=1)
    next_month = (current_month + timedelta(days=32)).replace(day=1)
    
    # Calculate stats
    total_income = FinancialTransaction.objects.filter(
        org=user_org,
        transaction_type='income',
        status='completed',
        transaction_date__gte=current_month,
        transaction_date__lt=next_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_expenses = FinancialTransaction.objects.filter(
        org=user_org,
        transaction_type='expense',
        status='completed',
        transaction_date__gte=current_month,
        transaction_date__lt=next_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Recent transactions
    recent_transactions = FinancialTransaction.objects.filter(
        org=user_org
    ).order_by('-transaction_date')[:10]
    
    # Due recurring transactions
    due_recurring = RecurringTransaction.objects.filter(
        org=user_org,
        is_active=True,
        next_due_date__lte=timezone.now().date()
    )
    
    # Budget analysis
    active_budgets = Budget.objects.filter(
        org=user_org,
        is_active=True,
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    )
    
    # Calculate budget status
    budget_data = []
    for budget in active_budgets:
        spent = budget.get_spent_amount()
        remaining = budget.get_remaining_amount()
        percentage = budget.get_percentage_used()
        
        budget_data.append({
            'budget': budget,
            'spent': spent,
            'remaining': remaining,
            'percentage': percentage,
            'is_over': budget.is_over_budget()
        })
    
    # Monthly expense trends (last 6 months)
    monthly_trends = []
    for i in range(6):
        month_start = (current_month - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        
        month_expenses = FinancialTransaction.objects.filter(
            org=user_org,
            transaction_type='expense',
            status='completed',
            transaction_date__gte=month_start,
            transaction_date__lt=month_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        monthly_trends.append({
            'month': month_start.strftime('%B %Y'),
            'amount': float(month_expenses)
        })
    
    # Reverse to show chronological order
    monthly_trends.reverse()
    
    context = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_amount': total_income - total_expenses,
        'recent_transactions': recent_transactions,
        'due_recurring': due_recurring,
        'budget_data': budget_data,
        'monthly_trends': monthly_trends,
        'monthly_trends_json': json.dumps(monthly_trends),
        'current_month': current_month.strftime('%B %Y'),
    }
    
    # Add currency context
    context.update(get_template_currency_context(user_org))
    
    return render(request, 'finance/dashboard.html', context)


class TransactionListView(LoginRequiredMixin, ListView):
    model = FinancialTransaction
    template_name = 'finance/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = FinancialTransaction.objects.filter(
            org=self.request.user.profile.org
        ).order_by('-transaction_date')
        
        # Apply search filters
        search_form = TransactionSearchForm(self.request.GET, user=self.request.user)
        if search_form.is_valid():
            search = search_form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(transaction_id__icontains=search) |
                    Q(reference_number__icontains=search)
                )
            
            transaction_type = search_form.cleaned_data.get('transaction_type')
            if transaction_type:
                queryset = queryset.filter(transaction_type=transaction_type)
            
            status = search_form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            category = search_form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            start_date = search_form.cleaned_data.get('start_date')
            if start_date:
                queryset = queryset.filter(transaction_date__gte=start_date)
            
            end_date = search_form.cleaned_data.get('end_date')
            if end_date:
                queryset = queryset.filter(transaction_date__lte=end_date)
            
            min_amount = search_form.cleaned_data.get('min_amount')
            if min_amount:
                queryset = queryset.filter(amount__gte=min_amount)
            
            max_amount = search_form.cleaned_data.get('max_amount')
            if max_amount:
                queryset = queryset.filter(amount__lte=max_amount)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = TransactionSearchForm(self.request.GET, user=self.request.user)
        context['bulk_form'] = BulkTransactionForm()
        
        # Summary stats for current filter
        queryset = self.get_queryset()
        context['total_count'] = queryset.count()
        context['total_amount'] = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Add currency context
        context.update(get_template_currency_context(self.request.user.profile.org))
        
        return context


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = FinancialTransaction
    form_class = FinancialTransactionForm
    template_name = 'finance/transaction_form.html'
    success_url = reverse_lazy('finance:transaction_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_template_currency_context(self.request.user.profile.org))
        return context
    
    def form_valid(self, form):
        form.instance.org = self.request.user.profile.org
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Transaction created successfully!')
        return super().form_valid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = FinancialTransaction
    form_class = FinancialTransactionForm
    template_name = 'finance/transaction_form.html'
    success_url = reverse_lazy('finance:transaction_list')
    
    def get_queryset(self):
        return FinancialTransaction.objects.filter(org=self.request.user.profile.org)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_template_currency_context(self.request.user.profile.org))
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Transaction updated successfully!')
        return super().form_valid(form)


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = FinancialTransaction
    template_name = 'finance/transaction_confirm_delete.html'
    success_url = reverse_lazy('finance:transaction_list')
    
    def get_queryset(self):
        return FinancialTransaction.objects.filter(org=self.request.user.profile.org)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Transaction deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def transaction_detail(request, slug):
    """Detailed view of a transaction"""
    transaction = get_object_or_404(
        FinancialTransaction,
        slug=slug,
        org=request.user.profile.org
    )
    
    # Get related transactions if any
    related_transactions = FinancialTransaction.objects.filter(
        org=request.user.profile.org,
        category=transaction.category
    ).exclude(id=transaction.id)[:5]
    
    context = {
        'transaction': transaction,
        'related_transactions': related_transactions,
    }
    
    # Add currency context
    context.update(get_template_currency_context(request.user.profile.org))
    
    return render(request, 'finance/transaction_detail.html', context)


# Recurring Transactions Views
class RecurringTransactionListView(LoginRequiredMixin, ListView):
    model = RecurringTransaction
    template_name = 'finance/recurring_transaction_list.html'
    context_object_name = 'recurring_transactions'
    paginate_by = 25
    
    def get_queryset(self):
        return RecurringTransaction.objects.filter(
            org=self.request.user.profile.org
        ).order_by('-next_due_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_org = self.request.user.profile.org
        
        # Get recurring transactions
        recurring_transactions = self.get_queryset()
        
        # Calculate statistics
        monthly_income = recurring_transactions.filter(
            transaction_type='income',
            frequency='monthly',
            is_active=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        monthly_expenses = recurring_transactions.filter(
            transaction_type='expense',
            frequency='monthly',
            is_active=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Count due transactions
        due_count = recurring_transactions.filter(
            is_active=True,
            next_due_date__lte=timezone.now().date()
        ).count()
        
        context.update({
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'due_count': due_count,
        })
        
        # Add currency context
        context.update(get_template_currency_context(user_org))
        
        return context


class RecurringTransactionCreateView(LoginRequiredMixin, CreateView):
    model = RecurringTransaction
    form_class = RecurringTransactionForm
    template_name = 'finance/recurring_transaction_form.html'
    success_url = reverse_lazy('finance:recurring_transaction_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.org = self.request.user.profile.org
        form.instance.created_by = self.request.user
        form.instance.next_due_date = form.instance.start_date
        messages.success(self.request, 'Recurring transaction created successfully!')
        return super().form_valid(form)


class RecurringTransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = RecurringTransaction
    form_class = RecurringTransactionForm
    template_name = 'finance/recurring_transaction_form.html'
    success_url = reverse_lazy('finance:recurring_transaction_list')
    
    def get_queryset(self):
        return RecurringTransaction.objects.filter(org=self.request.user.profile.org)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Recurring transaction updated successfully!')
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def process_recurring_transactions(request):
    """Process all due recurring transactions"""
    user_org = request.user.profile.org
    
    due_recurring = RecurringTransaction.objects.filter(
        org=user_org,
        is_active=True,
        auto_create=True,
        next_due_date__lte=timezone.now().date()
    )
    
    created_count = 0
    for recurring in due_recurring:
        try:
            transaction = recurring.create_transaction()
            created_count += 1
        except Exception as e:
            messages.error(request, f'Error creating transaction for {recurring.title}: {str(e)}')
    
    if created_count > 0:
        messages.success(request, f'Created {created_count} transactions from recurring templates.')
    else:
        messages.info(request, 'No due recurring transactions found.')
    
    return redirect('finance:recurring_transaction_list')


# Budget Views
class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = 'finance/budget_list.html'
    context_object_name = 'budgets'
    paginate_by = 25
    
    def get_queryset(self):
        return Budget.objects.filter(
            org=self.request.user.profile.org
        ).order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate budget summaries
        budgets = context['budgets']
        for budget in budgets:
            budget.spent_amount = budget.get_spent_amount()
            budget.remaining_amount = budget.get_remaining_amount()
            budget.percentage_used = budget.get_percentage_used()
            budget.is_over = budget.is_over_budget()
        
        # Add currency context
        context.update(get_template_currency_context(self.request.user.profile.org))
        
        return context


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'finance/budget_form.html'
    success_url = reverse_lazy('finance:budget_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_template_currency_context(self.request.user.profile.org))
        return context
    
    def form_valid(self, form):
        form.instance.org = self.request.user.profile.org
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Budget created successfully!')
        return super().form_valid(form)


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'finance/budget_form.html'
    success_url = reverse_lazy('finance:budget_list')
    
    def get_queryset(self):
        return Budget.objects.filter(org=self.request.user.profile.org)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_template_currency_context(self.request.user.profile.org))
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Budget updated successfully!')
        return super().form_valid(form)


@login_required
def budget_detail(request, slug):
    """Detailed view of a budget with spending analysis"""
    budget = get_object_or_404(Budget, slug=slug, org=request.user.profile.org)
    
    # Get transactions for this budget
    transactions = FinancialTransaction.objects.filter(
        org=request.user.profile.org,
        transaction_type='expense',
        status='completed',
        transaction_date__gte=budget.start_date,
        transaction_date__lte=budget.end_date
    )
    
    if budget.category:
        transactions = transactions.filter(category=budget.category)
    
    # Calculate spending over time
    spending_data = []
    current_date = budget.start_date
    cumulative_spending = Decimal('0.00')
    
    while current_date <= budget.end_date:
        daily_spending = transactions.filter(
            transaction_date__date=current_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        cumulative_spending += daily_spending
        
        spending_data.append({
            'date': current_date,
            'daily_spending': daily_spending,
            'cumulative_spending': cumulative_spending
        })
        
        current_date += timedelta(days=1)
    
    context = {
        'budget': budget,
        'transactions': transactions.order_by('-transaction_date'),
        'spending_data': spending_data,
        'spent_amount': budget.get_spent_amount(),
        'remaining_amount': budget.get_remaining_amount(),
        'percentage_used': budget.get_percentage_used(),
        'is_over_budget': budget.is_over_budget(),
    }
    
    # Add currency context
    context.update(get_template_currency_context(request.user.profile.org))
    
    return render(request, 'finance/budget_detail.html', context)


# Category Views
class CategoryListView(LoginRequiredMixin, ListView):
    model = TransactionCategory
    template_name = 'finance/category_list.html'
    context_object_name = 'categories'
    paginate_by = 25
    
    def get_queryset(self):
        return TransactionCategory.objects.filter(
            org=self.request.user.profile.org
        ).order_by('name')


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = TransactionCategory
    form_class = TransactionCategoryForm
    template_name = 'finance/category_form.html'
    success_url = reverse_lazy('finance:category_list')
    
    def form_valid(self, form):
        form.instance.org = self.request.user.profile.org
        response = super().form_valid(form)
        
        # Handle AJAX requests
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'category': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'slug': self.object.slug
                }
            })
        
        messages.success(self.request, 'Category created successfully!')
        return response
    
    def form_invalid(self, form):
        # Handle AJAX requests
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        
        return super().form_invalid(form)


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = TransactionCategory
    form_class = TransactionCategoryForm
    template_name = 'finance/category_form.html'
    success_url = reverse_lazy('finance:category_list')
    
    def get_queryset(self):
        return TransactionCategory.objects.filter(org=self.request.user.profile.org)
    
    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully!')
        return super().form_valid(form)


# Report Views
@login_required
def reports_dashboard(request):
    """Finance reports dashboard"""
    user_org = request.user.profile.org
    
    # Get recent reports
    recent_reports = FinancialReport.objects.filter(
        org=user_org
    ).order_by('-generated_at')[:10]
    
    context = {
        'recent_reports': recent_reports,
        'report_types': FinancialReport.REPORT_TYPES,
    }
    
    return render(request, 'finance/reports_dashboard.html', context)


@login_required
def generate_report(request):
    """Generate a new financial report"""
    if request.method == 'POST':
        form = FinancialReportForm(request.POST, user=request.user)
        if form.is_valid():
            report = form.save(commit=False)
            report.org = request.user.profile.org
            report.generated_by = request.user
            
            # Generate report data based on type
            report_data = generate_report_data(report)
            report.report_data = report_data
            
            report.save()
            messages.success(request, 'Report generated successfully!')
            return redirect('finance:report_detail', slug=report.slug)
    else:
        form = FinancialReportForm(user=request.user)
    
    return render(request, 'finance/generate_report.html', {'form': form})


def generate_report_data(report):
    """Generate report data based on report type"""
    org = report.org
    start_date = report.start_date
    end_date = report.end_date
    category = report.category
    
    base_query = FinancialTransaction.objects.filter(
        org=org,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
        status='completed'
    )
    
    if category:
        base_query = base_query.filter(category=category)
    
    if report.report_type == 'income_statement':
        income = base_query.filter(transaction_type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        expenses = base_query.filter(transaction_type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        return {
            'income': float(income),
            'expenses': float(expenses),
            'net_income': float(income - expenses),
            'period': f"{start_date} to {end_date}",
        }
    
    elif report.report_type == 'expense_report':
        expenses_by_category = base_query.filter(
            transaction_type='expense'
        ).values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        return {
            'expenses_by_category': list(expenses_by_category),
            'total_expenses': float(base_query.filter(transaction_type='expense').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')),
            'period': f"{start_date} to {end_date}",
        }
    
    elif report.report_type == 'budget_analysis':
        budgets = Budget.objects.filter(
            org=org,
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        budget_data = []
        for budget in budgets:
            budget_data.append({
                'name': budget.name,
                'budgeted': float(budget.budgeted_amount),
                'spent': float(budget.get_spent_amount()),
                'remaining': float(budget.get_remaining_amount()),
                'percentage': budget.get_percentage_used(),
                'over_budget': budget.is_over_budget()
            })
        
        return {
            'budgets': budget_data,
            'period': f"{start_date} to {end_date}",
        }
    
    elif report.report_type == 'cash_flow':
        # Monthly cash flow
        monthly_data = []
        current_date = start_date.replace(day=1)
        
        while current_date <= end_date:
            next_month = (current_date + timedelta(days=32)).replace(day=1)
            
            month_income = base_query.filter(
                transaction_type='income',
                transaction_date__gte=current_date,
                transaction_date__lt=next_month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            month_expenses = base_query.filter(
                transaction_type='expense',
                transaction_date__gte=current_date,
                transaction_date__lt=next_month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            monthly_data.append({
                'month': current_date.strftime('%Y-%m'),
                'income': float(month_income),
                'expenses': float(month_expenses),
                'net_flow': float(month_income - month_expenses)
            })
            
            current_date = next_month
        
        return {
            'monthly_data': monthly_data,
            'period': f"{start_date} to {end_date}",
        }
    
    elif report.report_type == 'category_breakdown':
        categories = TransactionCategory.objects.filter(org=org)
        category_data = []
        
        for cat in categories:
            cat_transactions = base_query.filter(category=cat)
            income = cat_transactions.filter(transaction_type='income').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            expenses = cat_transactions.filter(transaction_type='expense').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            category_data.append({
                'name': cat.name,
                'income': float(income),
                'expenses': float(expenses),
                'net': float(income - expenses),
                'transaction_count': cat_transactions.count()
            })
        
        return {
            'categories': category_data,
            'period': f"{start_date} to {end_date}",
        }
    
    return {}


@login_required
def report_detail(request, slug):
    """View a generated report"""
    report = get_object_or_404(FinancialReport, slug=slug, org=request.user.profile.org)
    
    return render(request, 'finance/report_detail.html', {'report': report})


@login_required
def export_transactions_csv(request):
    """Export transactions to CSV"""
    user_org = request.user.profile.org
    
    # Apply same filters as transaction list
    search_form = TransactionSearchForm(request.GET, user=request.user)
    transactions = FinancialTransaction.objects.filter(org=user_org)
    
    if search_form.is_valid():
        # Apply filters (same logic as in TransactionListView)
        search = search_form.cleaned_data.get('search')
        if search:
            transactions = transactions.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(transaction_id__icontains=search)
            )
        
        # Add other filters...
        transaction_type = search_form.cleaned_data.get('transaction_type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        status = search_form.cleaned_data.get('status')
        if status:
            transactions = transactions.filter(status=status)
        
        category = search_form.cleaned_data.get('category')
        if category:
            transactions = transactions.filter(category=category)
        
        start_date = search_form.cleaned_data.get('start_date')
        if start_date:
            transactions = transactions.filter(transaction_date__gte=start_date)
        
        end_date = search_form.cleaned_data.get('end_date')
        if end_date:
            transactions = transactions.filter(transaction_date__lte=end_date)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID', 'Title', 'Description', 'Amount', 'Type', 'Status',
        'Category', 'Payment Method', 'Date', 'Reference', 'Created By'
    ])
    
    for transaction in transactions:
        writer.writerow([
            transaction.transaction_id,
            transaction.title,
            transaction.description,
            transaction.amount,
            transaction.get_transaction_type_display(),
            transaction.get_status_display(),
            transaction.category.name if transaction.category else '',
            transaction.get_payment_method_display(),
            transaction.transaction_date.strftime('%Y-%m-%d %H:%M'),
            transaction.reference_number,
            transaction.created_by.email if transaction.created_by else ''
        ])
    
    return response


@login_required
@require_http_methods(["POST"])
def bulk_transaction_action(request):
    """Handle bulk actions on transactions"""
    form = BulkTransactionForm(request.POST)
    if form.is_valid():
        action = form.cleaned_data['action']
        transaction_ids = form.cleaned_data['selected_transactions'].split(',')
        
        transactions = FinancialTransaction.objects.filter(
            id__in=transaction_ids,
            org=request.user.profile.org
        )
        
        if action == 'delete':
            count = transactions.count()
            transactions.delete()
            messages.success(request, f'Deleted {count} transactions.')
        
        elif action == 'mark_completed':
            count = transactions.update(status='completed')
            messages.success(request, f'Marked {count} transactions as completed.')
        
        elif action == 'mark_pending':
            count = transactions.update(status='pending')
            messages.success(request, f'Marked {count} transactions as pending.')
        
        elif action == 'mark_failed':
            count = transactions.update(status='failed')
            messages.success(request, f'Marked {count} transactions as failed.')
        
        elif action == 'export_csv':
            # Redirect to CSV export with selected IDs
            return redirect(f"{reverse_lazy('finance:export_csv')}?ids={','.join(transaction_ids)}")
        
        else:
            messages.error(request, 'Invalid action selected.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Invalid action selected.'})
    
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid form data.'})
        messages.error(request, 'Invalid form data.')
    
    # If it's an AJAX request, return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('finance:transaction_list')


@login_required
def api_transaction_stats(request):
    """API endpoint for transaction statistics"""
    user_org = request.user.profile.org
    
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        return JsonResponse({'error': 'Start date and end date are required'}, status=400)
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    transactions = FinancialTransaction.objects.filter(
        org=user_org,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
        status='completed'
    )
    
    # Calculate stats
    income = transactions.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    expenses = transactions.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Category breakdown
    categories = transactions.values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    return JsonResponse({
        'income': float(income),
        'expenses': float(expenses),
        'net': float(income - expenses),
        'transaction_count': transactions.count(),
        'categories': list(categories),
        'period': f"{start_date} to {end_date}"
    })


@login_required
@require_http_methods(["POST"])
def mark_transaction_complete(request, slug):
    """Mark a single transaction as complete"""
    transaction = get_object_or_404(
        FinancialTransaction,
        slug=slug,
        org=request.user.profile.org
    )
    
    # Check if transaction is already completed
    if transaction.status == 'completed':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Transaction is already completed.'})
        messages.warning(request, 'Transaction is already completed.')
        return redirect('finance:transaction_detail', slug=slug)
    
    # Mark as completed
    transaction.status = 'completed'
    transaction.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Transaction marked as completed.'})
    
    messages.success(request, 'Transaction marked as completed.')
    return redirect('finance:transaction_detail', slug=slug)
