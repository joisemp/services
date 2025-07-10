from django import forms
from .models import Purchase, PurchaseItem, ShoppingListItem
from decimal import Decimal

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
