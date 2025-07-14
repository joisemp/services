from django import forms
from core.models import UserProfile
from django.contrib.auth import get_user_model
from .models import WorkCategory, ShoppingList, ShoppingListItem, Purchase, PurchaseItem

User = get_user_model()

USER_TYPE_CHOICES = [
    (k, v) for k, v in UserProfile.USER_TYPE_CHOICES if k != 'general_user'
]

class AddGeneralUserForm(forms.Form):
    phone = forms.CharField(max_length=20, label='Phone Number')
    first_name = forms.CharField(max_length=255, required=False)
    last_name = forms.CharField(max_length=255, required=False)

class AddOtherUserForm(forms.Form):
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, label='User Type')
    skills = forms.ModelMultipleChoiceField(
        queryset=WorkCategory.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Work Categories (Skills)'
    )

    def __init__(self, *args, **kwargs):
        org = kwargs.pop('org', None)
        super().__init__(*args, **kwargs)
        if org:
            self.fields['skills'].queryset = WorkCategory.objects.filter(org=org)
        else:
            self.fields['skills'].queryset = WorkCategory.objects.all()

class WorkCategoryForm(forms.ModelForm):
    class Meta:
        model = WorkCategory
        fields = ['name', 'description']


class ShoppingListForm(forms.ModelForm):
    class Meta:
        model = ShoppingList
        fields = ['name', 'description', 'priority', 'budget_limit']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'budget_limit': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['priority'].widget.attrs.update({'class': 'form-select'})
        self.fields['budget_limit'].widget.attrs.update({'class': 'form-control'})


class ShoppingListItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingListItem
        fields = ['item_name', 'description', 'quantity', 'estimated_cost', 'supplier', 'category', 'notes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'estimated_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'quantity': forms.NumberInput(attrs={'min': '1'}),
        }
        labels = {
            'estimated_cost': 'Estimated Cost (per unit)',
        }
        help_texts = {
            'estimated_cost': 'Enter the cost per single unit. The total will be calculated automatically.',
        }

    def __init__(self, *args, **kwargs):
        org = kwargs.pop('org', None)
        super().__init__(*args, **kwargs)
        if org:
            self.fields['category'].queryset = WorkCategory.objects.filter(org=org)
        else:
            self.fields['category'].queryset = WorkCategory.objects.all()
        
        # Add CSS classes
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier_name', 'supplier_contact', 'expected_delivery', 'notes']
        widgets = {
            'expected_delivery': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ['quantity_ordered', 'unit_cost', 'notes']
        widgets = {
            'quantity_ordered': forms.NumberInput(attrs={'min': '1'}),
            'unit_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class ShoppingListApprovalForm(forms.ModelForm):
    approval_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False,
        help_text='Optional comment for approval or rejection'
    )
    
    class Meta:
        model = ShoppingList
        fields = ['status']
        widgets = {
            'status': forms.Select(choices=[
                ('approved', 'Approved'),
                ('rejected', 'Rejected'),
            ])
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].widget.attrs.update({'class': 'form-select'})


class PurchaseStatusForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['status', 'invoice_number', 'actual_delivery', 'notes']
        widgets = {
            'actual_delivery': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
