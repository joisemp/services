from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import (
    TransactionCategory,
    FinancialTransaction,
    RecurringTransaction,
    Budget,
    TransactionAttachment,
    FinancialReport
)


class TransactionCategoryForm(forms.ModelForm):
    class Meta:
        model = TransactionCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FinancialTransactionForm(forms.ModelForm):
    class Meta:
        model = FinancialTransaction
        fields = [
            'title', 'description', 'amount', 'transaction_type', 'payment_method',
            'status', 'category', 'transaction_date', 'reference_number',
            'receipt_image', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'transaction_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'receipt_image': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile') and user.profile.org:
            self.fields['category'].queryset = TransactionCategory.objects.filter(
                org=user.profile.org, is_active=True
            )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Amount must be greater than 0.")
        return amount

    def clean_transaction_date(self):
        transaction_date = self.cleaned_data.get('transaction_date')
        if transaction_date and transaction_date > timezone.now():
            raise ValidationError("Transaction date cannot be in the future.")
        return transaction_date


class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = [
            'title', 'description', 'amount', 'frequency', 'start_date',
            'end_date', 'transaction_type', 'payment_method', 'category',
            'is_active', 'auto_create'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_create': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile') and user.profile.org:
            self.fields['category'].queryset = TransactionCategory.objects.filter(
                org=user.profile.org, is_active=True
            )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Amount must be greater than 0.")
        return amount

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date and start_date < timezone.now().date():
            raise ValidationError("Start date cannot be in the past.")
        return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date.")
        
        return cleaned_data


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = [
            'name', 'description', 'category', 'budgeted_amount', 'period',
            'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'budgeted_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'period': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile') and user.profile.org:
            self.fields['category'].queryset = TransactionCategory.objects.filter(
                org=user.profile.org, is_active=True
            )
            # Add empty option for overall budget
            self.fields['category'].empty_label = "Overall Budget (All Categories)"

    def clean_budgeted_amount(self):
        amount = self.cleaned_data.get('budgeted_amount')
        if amount and amount <= 0:
            raise ValidationError("Budget amount must be greater than 0.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date.")
        
        return cleaned_data


class TransactionAttachmentForm(forms.ModelForm):
    class Meta:
        model = TransactionAttachment
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 10MB.")
            
            # Check file type
            allowed_types = [
                'application/pdf',
                'image/jpeg',
                'image/png',
                'image/gif',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/plain'
            ]
            
            if file.content_type not in allowed_types:
                raise ValidationError("File type not allowed. Please upload PDF, Word, Excel, or image files.")
        
        return file


class FinancialReportForm(forms.ModelForm):
    class Meta:
        model = FinancialReport
        fields = ['name', 'report_type', 'start_date', 'end_date', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile') and user.profile.org:
            self.fields['category'].queryset = TransactionCategory.objects.filter(
                org=user.profile.org, is_active=True
            )
            # Add empty option for all categories
            self.fields['category'].empty_label = "All Categories"

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date.")
        
        # Don't allow reports for future dates
        if end_date and end_date > timezone.now().date():
            raise ValidationError("End date cannot be in the future.")
        
        return cleaned_data


class TransactionSearchForm(forms.Form):
    """Form for searching and filtering transactions"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search transactions...'
        })
    )
    
    transaction_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + FinancialTransaction.TRANSACTION_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + FinancialTransaction.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=TransactionCategory.objects.none(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    min_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )
    
    max_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile') and user.profile.org:
            self.fields['category'].queryset = TransactionCategory.objects.filter(
                org=user.profile.org, is_active=True
            )


class BulkTransactionForm(forms.Form):
    """Form for bulk operations on transactions"""
    BULK_ACTIONS = [
        ('', 'Select Action'),
        ('delete', 'Delete Selected'),
        ('mark_completed', 'Mark as Completed'),
        ('mark_pending', 'Mark as Pending'),
        ('mark_failed', 'Mark as Failed'),
        ('export_csv', 'Export to CSV'),
        ('export_pdf', 'Export to PDF'),
    ]
    
    action = forms.ChoiceField(
        choices=BULK_ACTIONS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    selected_transactions = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    confirm = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
