from django import forms
from config.mixins.form_mixin import BootstrapFormMixin
from .models import Warehouse, Category


class WarehouseForm(BootstrapFormMixin, forms.ModelForm):
	class Meta:
		model = Warehouse
		fields = ['name', 'location']
		labels = {
			'name': 'Warehouse Name',
			'location': 'Location',
		}


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
	class Meta:
		model = Category
		fields = ['name', 'description']
		labels = {
			'name': 'Category Name',
			'description': 'Description',
		}
		widgets = {
			'description': forms.Textarea(attrs={'rows': 4}),
		}


