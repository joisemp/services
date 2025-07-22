from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from config.utils import generate_unique_slug
from django.conf import settings
from .currency import CurrencyMixin, get_currency_info, format_currency

# Create your models here.

class TransactionCategory(models.Model):
    """Categories for financial transactions"""
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    org = models.ForeignKey('core.Organisation', related_name='transaction_categories', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Transaction Category"
        verbose_name_plural = "Transaction Categories"
        unique_together = ['name', 'org']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.name}-{self.org.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.org.name})"


class FinancialTransaction(models.Model, CurrencyMixin):
    """Main model for all financial transactions"""
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
        ('refund', 'Refund'),
    ]

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('check', 'Check'),
        ('digital_wallet', 'Digital Wallet'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    # Basic transaction info
    transaction_id = models.CharField(max_length=50, unique=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='expense')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Categorization
    category = models.ForeignKey(TransactionCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Organization and user
    org = models.ForeignKey('core.Organisation', related_name='financial_transactions', on_delete=models.CASCADE)
    space = models.ForeignKey('service_management.Spaces', related_name='financial_transactions', on_delete=models.CASCADE, null=True, blank=True, help_text="Space where this transaction was recorded")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_transactions', on_delete=models.SET_NULL, null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='approved_transactions', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Generic foreign key for linking to other models (issues, services, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Timestamps
    transaction_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional fields
    reference_number = models.CharField(max_length=100, blank=True)
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    notes = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False)
    
    # Slug for URL generation
    slug = models.SlugField(unique=True, db_index=True, blank=True)

    class Meta:
        verbose_name = "Financial Transaction"
        verbose_name_plural = "Financial Transactions"
        ordering = ['-transaction_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            # Generate unique transaction ID
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.transaction_id = f"TXN{timestamp}{self.pk or ''}"
        
        if not self.slug:
            base_slug = slugify(f"{self.title}-{self.transaction_id}")
            self.slug = generate_unique_slug(self, base_slug)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.amount} ({self.transaction_type})"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('finance:transaction_detail', kwargs={'slug': self.slug})


class RecurringTransaction(models.Model, CurrencyMixin):
    """Model for recurring financial transactions"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    # Recurrence settings
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank for indefinite recurrence")
    next_due_date = models.DateField()
    
    # Transaction template
    transaction_type = models.CharField(max_length=20, choices=FinancialTransaction.TRANSACTION_TYPES, default='expense')
    payment_method = models.CharField(max_length=20, choices=FinancialTransaction.PAYMENT_METHODS, default='cash')
    category = models.ForeignKey(TransactionCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Organization and user
    org = models.ForeignKey('core.Organisation', related_name='recurring_transactions', on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_recurring_transactions', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    auto_create = models.BooleanField(default=True, help_text="Automatically create transactions when due")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Slug for URL generation
    slug = models.SlugField(unique=True, db_index=True, blank=True)

    class Meta:
        verbose_name = "Recurring Transaction"
        verbose_name_plural = "Recurring Transactions"
        ordering = ['next_due_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.title}-recurring")
            self.slug = generate_unique_slug(self, base_slug)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.amount} ({self.frequency})"

    def calculate_next_due_date(self):
        """Calculate the next due date based on frequency"""
        if self.frequency == 'daily':
            return self.next_due_date + timedelta(days=1)
        elif self.frequency == 'weekly':
            return self.next_due_date + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            # Add one month
            from calendar import monthrange
            next_month = self.next_due_date.month + 1
            next_year = self.next_due_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            
            # Handle day overflow (e.g., Jan 31 -> Feb 28)
            max_day = monthrange(next_year, next_month)[1]
            next_day = min(self.next_due_date.day, max_day)
            
            return self.next_due_date.replace(year=next_year, month=next_month, day=next_day)
        elif self.frequency == 'quarterly':
            # Add 3 months
            from dateutil.relativedelta import relativedelta
            return self.next_due_date + relativedelta(months=3)
        elif self.frequency == 'yearly':
            # Add one year
            from dateutil.relativedelta import relativedelta
            return self.next_due_date + relativedelta(years=1)
        
        return self.next_due_date

    def create_transaction(self):
        """Create a new transaction based on this recurring template"""
        transaction = FinancialTransaction.objects.create(
            title=self.title,
            description=self.description,
            amount=self.amount,
            transaction_type=self.transaction_type,
            payment_method=self.payment_method,
            category=self.category,
            org=self.org,
            created_by=self.created_by,
            transaction_date=timezone.now(),
            is_recurring=True,
            notes=f"Auto-generated from recurring transaction: {self.title}"
        )
        
        # Update next due date
        self.next_due_date = self.calculate_next_due_date()
        self.save()
        
        return transaction

    def is_due(self):
        """Check if the recurring transaction is due"""
        return self.next_due_date <= timezone.now().date()


class Budget(models.Model, CurrencyMixin):
    """Budget management for categories and time periods"""
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Budget settings
    category = models.ForeignKey(TransactionCategory, on_delete=models.CASCADE, null=True, blank=True, help_text="Leave blank for overall budget")
    budgeted_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='monthly')
    
    # Time period
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Organization
    org = models.ForeignKey('core.Organisation', related_name='budgets', on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_budgets', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Slug for URL generation
    slug = models.SlugField(unique=True, db_index=True, blank=True)

    class Meta:
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        ordering = ['-start_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.name}-budget")
            self.slug = generate_unique_slug(self, base_slug)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.budgeted_amount} ({self.period})"

    def get_spent_amount(self):
        """Calculate total spent amount for this budget"""
        transactions = FinancialTransaction.objects.filter(
            org=self.org,
            transaction_type='expense',
            status='completed',
            transaction_date__gte=self.start_date,
            transaction_date__lte=self.end_date
        )
        
        if self.category:
            transactions = transactions.filter(category=self.category)
        
        total = transactions.aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    def get_remaining_amount(self):
        """Calculate remaining budget amount"""
        return self.budgeted_amount - self.get_spent_amount()

    def get_percentage_used(self):
        """Calculate percentage of budget used"""
        spent = self.get_spent_amount()
        if self.budgeted_amount > 0:
            return (spent / self.budgeted_amount) * 100
        return 0

    def is_over_budget(self):
        """Check if budget is exceeded"""
        return self.get_spent_amount() > self.budgeted_amount


class TransactionAttachment(models.Model):
    """File attachments for transactions"""
    transaction = models.ForeignKey(FinancialTransaction, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='transaction_attachments/')
    filename = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Transaction Attachment"
        verbose_name_plural = "Transaction Attachments"

    def __str__(self):
        return f"{self.filename} - {self.transaction.title}"


class FinancialReport(models.Model):
    """Pre-generated financial reports"""
    REPORT_TYPES = [
        ('income_statement', 'Income Statement'),
        ('expense_report', 'Expense Report'),
        ('budget_analysis', 'Budget Analysis'),
        ('cash_flow', 'Cash Flow Statement'),
        ('category_breakdown', 'Category Breakdown'),
    ]

    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    
    # Report parameters
    start_date = models.DateField()
    end_date = models.DateField()
    category = models.ForeignKey(TransactionCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Organization
    org = models.ForeignKey('core.Organisation', related_name='financial_reports', on_delete=models.CASCADE)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='generated_reports', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Report data (stored as JSON)
    report_data = models.JSONField(default=dict, blank=True)
    
    # File export
    pdf_file = models.FileField(upload_to='financial_reports/', blank=True, null=True)
    
    # Timestamps
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Slug for URL generation
    slug = models.SlugField(unique=True, db_index=True, blank=True)

    class Meta:
        verbose_name = "Financial Report"
        verbose_name_plural = "Financial Reports"
        ordering = ['-generated_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.name}-report")
            self.slug = generate_unique_slug(self, base_slug)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.report_type})"
