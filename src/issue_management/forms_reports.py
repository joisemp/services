"""
Forms for performance report generation
"""

from django import forms
from django.utils import timezone
from datetime import timedelta
from core.models import User
from config.mixins.form_mixin import BootstrapFormMixin


class PerformanceReportForm(BootstrapFormMixin, forms.Form):
    """Form for configuring performance report parameters"""
    
    PERIOD_CHOICES = [
        ('7', 'Last 7 Days'),
        ('30', 'Last 30 Days'),
        ('90', 'Last 90 Days'),
        ('custom', 'Custom Date Range'),
    ]
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        initial='30',
        required=True,
        label='Report Period',
        help_text='Select the time period for the report'
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Start Date',
        help_text='Required if Custom Date Range is selected'
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='End Date',
        help_text='Required if Custom Date Range is selected'
    )
    
    include_supervisors = forms.BooleanField(
        initial=True,
        required=False,
        label='Include Supervisors',
        help_text='Include supervisor performance metrics in the report'
    )
    
    include_maintainers = forms.BooleanField(
        initial=True,
        required=False,
        label='Include Maintainers',
        help_text='Include maintainer performance metrics in the report'
    )
    
    specific_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Specific Users',
        help_text='Leave empty to include all users of selected roles'
    )
    
    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if organization:
            # Only show supervisors and maintainers from the organization
            self.fields['specific_users'].queryset = User.objects.filter(
                organization=organization,
                user_type__in=['supervisor', 'maintainer'],
                is_active=True
            ).order_by('user_type', 'first_name', 'last_name')
    
    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('period')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        include_supervisors = cleaned_data.get('include_supervisors')
        include_maintainers = cleaned_data.get('include_maintainers')
        
        # Validate custom date range
        if period == 'custom':
            if not start_date or not end_date:
                raise forms.ValidationError('Both start date and end date are required for custom date range.')
            
            if start_date > end_date:
                raise forms.ValidationError('Start date must be before end date.')
            
            # Ensure dates are not in the future
            today = timezone.now().date()
            if end_date > today:
                raise forms.ValidationError('End date cannot be in the future.')
        
        # Ensure at least one role is selected
        if not include_supervisors and not include_maintainers:
            raise forms.ValidationError('Please select at least one role (Supervisors or Maintainers).')
        
        return cleaned_data
    
    def get_date_range(self):
        """Calculate and return the date range based on form data"""
        cleaned_data = self.cleaned_data
        period = cleaned_data.get('period')
        
        if period == 'custom':
            start_date = cleaned_data.get('start_date')
            end_date = cleaned_data.get('end_date')
            # Convert to datetime for consistency
            start_datetime = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
            end_datetime = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time()))
            return start_datetime, end_datetime
        else:
            days = int(period)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            return start_date, end_date
    
    def get_user_filter(self):
        """Get list of specific user IDs to include, or None for all users"""
        specific_users = self.cleaned_data.get('specific_users')
        if specific_users:
            return [user.id for user in specific_users]
        return None
