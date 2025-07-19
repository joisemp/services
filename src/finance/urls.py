from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Transactions
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/create/', views.TransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/bulk-action/', views.bulk_transaction_action, name='bulk_transaction_action'),
    path('transactions/<slug:slug>/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<slug:slug>/complete/', views.mark_transaction_complete, name='mark_transaction_complete'),
    path('transactions/<slug:slug>/edit/', views.TransactionUpdateView.as_view(), name='transaction_update'),
    path('transactions/<slug:slug>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
    
    # Recurring Transactions
    path('recurring/', views.RecurringTransactionListView.as_view(), name='recurring_transaction_list'),
    path('recurring/create/', views.RecurringTransactionCreateView.as_view(), name='recurring_transaction_create'),
    path('recurring/<slug:slug>/edit/', views.RecurringTransactionUpdateView.as_view(), name='recurring_transaction_update'),
    path('recurring/process/', views.process_recurring_transactions, name='process_recurring_transactions'),
    
    # Budgets
    path('budgets/', views.BudgetListView.as_view(), name='budget_list'),
    path('budgets/create/', views.BudgetCreateView.as_view(), name='budget_create'),
    path('budgets/<slug:slug>/', views.budget_detail, name='budget_detail'),
    path('budgets/<slug:slug>/edit/', views.BudgetUpdateView.as_view(), name='budget_update'),
    
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<slug:slug>/edit/', views.CategoryUpdateView.as_view(), name='category_update'),
    
    # Reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('reports/<slug:slug>/', views.report_detail, name='report_detail'),
    
    # Export
    path('export/csv/', views.export_transactions_csv, name='export_csv'),
    
    # API endpoints
    path('api/stats/', views.api_transaction_stats, name='api_transaction_stats'),
]