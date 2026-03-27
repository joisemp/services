from django import forms
from config.mixins.form_mixin import BootstrapFormMixin
from .models import Warehouse


class WarehouseForm(BootstrapFormMixin, forms.ModelForm):
	class Meta:
		model = Warehouse
		fields = ['name', 'location']
		labels = {
			'name': 'Warehouse Name',
			'location': 'Location',
		}

