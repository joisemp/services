"""
Django Forms for Fleet Management.
Contains form definitions for vehicle management, fleet operations, and related tasks.
"""
from django import forms
from config.mixins.form_mixin import BootstrapFormMixin

from fleet_management.models import Vehicle, Workshop


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


class WorkshopForm(BootstrapFormMixin, forms.ModelForm):
	class Meta:
		model = Workshop
		fields = [
			'name',
			'incharges',
			'notes',
		]
		widgets = {
			'incharges': forms.CheckboxSelectMultiple(),
			'notes': forms.Textarea(attrs={'rows': 4}),
		}

	def __init__(self, *args, **kwargs):
		self.org = kwargs.pop('org', None)
		super().__init__(*args, **kwargs)
		self.fields['incharges'].required = False
		self.fields['incharges'].widget.attrs['class'] = 'form-check-input'

		if self.org:
			self.fields['incharges'].queryset = self.org.users.filter(
				is_active=True,
				user_type__in=['maintainer', 'supervisor'],
			).order_by('first_name', 'last_name')
		else:
			self.fields['incharges'].queryset = self.fields['incharges'].queryset.none()

		self.fields['incharges'].help_text = 'Select zero or more maintainers/supervisors from your organization.'

	def clean_name(self):
		return self.cleaned_data['name'].strip()

	def clean_incharges(self):
		incharges = self.cleaned_data.get('incharges')
		if not self.org:
			if incharges:
				raise forms.ValidationError('Workshop incharges require an organization context.')
			return incharges

		invalid_incharges = incharges.exclude(
			organization=self.org,
			user_type__in=['maintainer', 'supervisor'],
		)
		if invalid_incharges.exists():
			raise forms.ValidationError('Only maintainers/supervisors in your organization can be assigned as incharges.')

		return incharges
