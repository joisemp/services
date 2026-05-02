"""
Django Forms for Fleet Management.
Contains form definitions for vehicle management, fleet operations, and related tasks.
"""
from django import forms
from config.mixins.form_mixin import BootstrapFormMixin

from fleet_management.models import Vehicle


class VehicleForm(BootstrapFormMixin, forms.ModelForm):
	class Meta:
		model = Vehicle
		fields = [
			'registration_number',
			'vehicle_type',
			'manufacturer',
			'model',
			'year',
			'notes',
		]
		widgets = {
			'notes': forms.Textarea(attrs={'rows': 4}),
			'year': forms.NumberInput(attrs={'min': 1900, 'max': 2100}),
		}

	def clean_registration_number(self):
		return self.cleaned_data['registration_number'].strip().upper()


class StatusChangeForm(forms.Form):
	"""Form for handling vehicle status changes via AJAX."""
	vehicle_id = forms.IntegerField(widget=forms.HiddenInput())
