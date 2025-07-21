from django import forms
from service_management.models import WorkCategory
from .models import ShoppingList, ShoppingListItem, Purchase, PurchaseItem
from decimal import Decimal


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


class PurchaseItemSelectForm(forms.Form):
    """Form for selecting which items to include in a purchase order with quantities"""
    
    def __init__(self, shopping_list_items, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for item in shopping_list_items:
            # Create a field for selecting this item
            self.fields[f'select_{item.id}'] = forms.BooleanField(
                required=False,
                label=f"Include {item.item_name}",
                initial=True
            )
            
            # Create a field for the quantity
            self.fields[f'quantity_{item.id}'] = forms.IntegerField(
                min_value=1,
                max_value=item.quantity,
                initial=item.quantity,
                required=False,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': '1',
                    'max': item.quantity
                })
            )
            
            # Add a hidden field to store the unit cost
            self.fields[f'unit_cost_{item.id}'] = forms.DecimalField(
                widget=forms.HiddenInput(),
                initial=Decimal(item.estimated_cost) / Decimal(item.quantity) if item.quantity > 0 else 0
            )
    
    def clean(self):
        cleaned_data = super().clean()
        at_least_one_selected = False
        
        for key, value in cleaned_data.items():
            if key.startswith('select_') and value:
                item_id = key.split('_')[1]
                quantity_key = f'quantity_{item_id}'
                
                # If item is selected, quantity is required
                if not cleaned_data.get(quantity_key):
                    self.add_error(quantity_key, "Quantity is required when item is selected.")
                else:
                    at_least_one_selected = True
        
        if not at_least_one_selected:
            raise forms.ValidationError("You must select at least one item for the purchase order.")
            
        return cleaned_data


class MultiShopPurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier_name', 'supplier_contact', 'expected_delivery', 'notes']
        widgets = {
            'expected_delivery': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'supplier_name': 'Shop/Supplier Name',
            'supplier_contact': 'Shop/Supplier Contact Details',
        }
        help_texts = {
            'supplier_name': 'Enter the name of the shop or supplier where these items will be purchased.',
            'supplier_contact': 'Enter phone, email or address for this supplier.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
