from django import forms
from django.contrib.auth import get_user_model
from .models import (
    Vehicle, VehicleType, VehicleMake, VehicleModel,
    VehicleDocument, MaintenanceRecord, VehicleComponent,
    VehicleComponentInstance, ComponentInspection
)

User = get_user_model()


class VehicleForm(forms.ModelForm):
    """Form for creating and updating vehicles"""
    
    class Meta:
        model = Vehicle
        fields = [
            'vehicle_model', 'license_plate', 'vin', 'year', 'color',
            'engine_capacity', 'fuel_type', 'transmission', 'mileage',
            'owner', 'assigned_to', 'status', 'purchase_date', 'purchase_price',
            'current_value', 'insurance_company', 'insurance_policy_number',
            'insurance_expiry', 'registration_expiry', 'last_service_date',
            'next_service_due', 'service_interval_km', 'notes', 'is_company_vehicle'
        ]
        widgets = {
            'vehicle_model': forms.Select(attrs={'class': 'form-select'}),
            'license_plate': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter license plate'
            }),
            'vin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter VIN (17 characters)'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1900,
                'max': 2030
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter vehicle color'
            }),
            'engine_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 0.1,
                'placeholder': 'Engine capacity in liters'
            }),
            'fuel_type': forms.Select(attrs={'class': 'form-select'}),
            'transmission': forms.Select(attrs={'class': 'form-select'}),
            'mileage': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Current mileage'
            }),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 0.01,
                'placeholder': 'Purchase price'
            }),
            'current_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 0.01,
                'placeholder': 'Current value'
            }),
            'insurance_company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Insurance company name'
            }),
            'insurance_policy_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Policy number'
            }),
            'insurance_expiry': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'registration_expiry': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'last_service_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'next_service_due': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'service_interval_km': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Service interval in km'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes'
            }),
            'is_company_vehicle': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'vehicle_model': forms.Select(attrs={
                'class': 'form-select',
                'hx-get': '/transportation/ajax/get-models/',
                'hx-target': '#id_vehicle_model',
                'hx-trigger': 'change'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner'].queryset = User.objects.filter(is_active=True)
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        self.fields['owner'].empty_label = "Select owner"
        self.fields['assigned_to'].empty_label = "Select assigned user"


class VehicleModelForm(forms.ModelForm):
    """Form for creating and updating vehicle models"""
    
    class Meta:
        model = VehicleModel
        fields = ['make', 'name', 'vehicle_type', 'year_introduced', 'year_discontinued', 'engine_types'
        ]
        widgets = {
            'make': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter model name'
            }),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'year_introduced': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1900,
                'max': 2030
            }),
            'year_discontinued': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1900,
                'max': 2030
            }),
            'engine_types': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Gasoline, Diesel, Electric, Hybrid'
            }),
        }


class QuickVehicleModelForm(forms.ModelForm):
    """Simplified form for quick vehicle model creation via HTMX"""
    
    class Meta:
        model = VehicleModel
        fields = ['make', 'name', 'vehicle_type']
        widgets = {
            'make': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter model name',
                'required': True
            }),
            'vehicle_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['make'].empty_label = "Select make"
        self.fields['vehicle_type'].empty_label = "Select vehicle type"


class VehicleDocumentForm(forms.ModelForm):
    """Form for uploading vehicle documents"""
    
    class Meta:
        model = VehicleDocument
        fields = ['document_type', 'title', 'document_file', 'expiry_date', 'notes']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Document title'
            }),
            'document_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes'
            }),
        }


class MaintenanceRecordForm(forms.ModelForm):
    """Form for creating maintenance records"""
    
    class Meta:
        model = MaintenanceRecord
        fields = [
            'vehicle', 'maintenance_type', 'date', 'mileage_at_service',
            'description', 'cost', 'service_provider', 'next_service_due_date',
            'next_service_due_mileage'
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'maintenance_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'mileage_at_service': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mileage at service'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the maintenance performed'
            }),
            'cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 0.01,
                'placeholder': 'Cost of maintenance'
            }),
            'service_provider': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Service provider name'
            }),
            'next_service_due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'next_service_due_mileage': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Next service due at mileage'
            }),
        }


class VehicleComponentForm(forms.ModelForm):
    """Form for creating vehicle components"""
    
    class Meta:
        model = VehicleComponent
        fields = ['name', 'category', 'description', 'is_critical']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Component name'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Component name'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Component description'
            }),
            'is_critical': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ComponentInspectionForm(forms.ModelForm):
    """Form for creating component inspections"""
    
    class Meta:
        model = ComponentInspection
        fields = [
            'inspection_date', 'inspection_type', 'result', 'condition_rating',
            'findings', 'recommendations', 'next_inspection_due', 'photos',
            'mileage_at_inspection', 'estimated_remaining_life', 'replacement_urgency'
        ]
        widgets = {
            'inspection_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'inspection_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Type of inspection'
            }),
            'result': forms.Select(attrs={'class': 'form-select'}),
            'condition_rating': forms.Select(attrs={'class': 'form-select'}),
            'findings': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed findings from inspection'
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Recommended actions'
            }),
            'next_inspection_due': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'photos': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png'
            }),
            'mileage_at_inspection': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mileage at inspection'
            }),
            'estimated_remaining_life': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Remaining life in km'
            }),
            'replacement_urgency': forms.Select(attrs={'class': 'form-select'}),
        }


class VehicleFilterForm(forms.Form):
    """Form for filtering vehicles"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search vehicles...',
            'hx-get': '/transportation/vehicles/',
            'hx-target': '#vehicle-list',
            'hx-trigger': 'keyup changed delay:500ms'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Vehicle.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '/transportation/vehicles/',
            'hx-target': '#vehicle-list',
            'hx-trigger': 'change'
        })
    )
    vehicle_type = forms.ModelChoiceField(
        queryset=VehicleType.objects.all(),
        required=False,
        empty_label="All Types",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '/transportation/vehicles/',
            'hx-target': '#vehicle-list',
            'hx-trigger': 'change'
        })
    )


class MaintenanceFilterForm(forms.Form):
    """Form for filtering maintenance records"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search maintenance records...',
            'hx-get': '/transportation/maintenance/',
            'hx-target': '#maintenance-list',
            'hx-trigger': 'keyup changed delay:500ms'
        })
    )
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.all(),
        required=False,
        empty_label="All Vehicles",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '/transportation/maintenance/',
            'hx-target': '#maintenance-list',
            'hx-trigger': 'change'
        })
    )
    maintenance_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + MaintenanceRecord.MAINTENANCE_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '/transportation/maintenance/',
            'hx-target': '#maintenance-list',
            'hx-trigger': 'change'
        })
    )


class QuickVehicleMakeForm(forms.ModelForm):
    """Simplified form for quick vehicle make creation via HTMX"""
    
    class Meta:
        model = VehicleMake
        fields = ['name', 'country']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter make name (e.g., Toyota, Ford)',
                'required': True
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country of origin (optional)'
            }),
        }


class QuickVehicleTypeForm(forms.ModelForm):
    """Simplified form for quick vehicle type creation via HTMX"""
    
    class Meta:
        model = VehicleType
        fields = ['name', 'description']
        widgets = {
            'name': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        organisation = kwargs.pop('organisation', None)
        super().__init__(*args, **kwargs)
        
        # Get existing vehicle types to exclude them from choices
        if organisation:
            existing_types = VehicleType.objects.filter(
                organisation=organisation
            ).values_list('name', flat=True)
        else:
            existing_types = VehicleType.objects.values_list('name', flat=True)
        available_choices = [choice for choice in VehicleType.TYPE_CHOICES if choice[0] not in existing_types]
        
        self.fields['name'].widget.choices = [('', 'Select vehicle type')] + available_choices
        
        # If no types are available, show a message
        if not available_choices:
            self.fields['name'].widget.choices = [('', 'All vehicle types are already created')]
            self.fields['name'].widget.attrs['disabled'] = True
