from django import forms
from config.mixins.form_mixin import BootstrapFormMixin
from .models import Warehouse, Category, Brand
from core.models import User


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


class BrandForm(BootstrapFormMixin, forms.ModelForm):
	class Meta:
		model = Brand
		fields = ['name', 'description']
		labels = {
			'name': 'Brand Name',
			'description': 'Description',
		}
		widgets = {
			'description': forms.Textarea(attrs={'rows': 4}),
		}


class WarehouseUserAddForm(BootstrapFormMixin, forms.Form):
	"""
	Form for adding maintainers and supervisors to a warehouse
	"""
	users = forms.MultipleChoiceField(
		widget=forms.CheckboxSelectMultiple,
		label="Select Users",
		help_text="Choose maintainers and supervisors to add to this warehouse"
	)

	def __init__(self, warehouse, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.warehouse = warehouse
		# Get only maintainer and supervisor users from the same organization who aren't already in this warehouse
		available_users = User.objects.filter(
			organization=warehouse.org,
			user_type__in=['maintainer', 'supervisor']
		).exclude(
			warehouses=warehouse
		).order_by('first_name', 'last_name')
		
		# Set choices for the multiple choice field (ensure keys are strings)
		self.fields['users'].choices = [
			(str(user.id), str(user)) for user in available_users
		]
		
		# Store available users for validation (use string keys to match choices)
		self.available_users = {str(user.id): user for user in available_users}

	def clean_users(self):
		"""
		Custom validation and conversion for users field
		"""
		user_ids = self.cleaned_data.get('users', [])
		if not user_ids:
			raise forms.ValidationError("Please select at least one user.")
		
		users = []
		for user_id in user_ids:
			if user_id not in self.available_users:
				raise forms.ValidationError("Invalid selection.")
			users.append(self.available_users[user_id])
		
		return users


class WarehouseUserRemoveForm(BootstrapFormMixin, forms.Form):
	"""
	Form for removing users from a warehouse
	"""
	user_id = forms.IntegerField(widget=forms.HiddenInput())

	def __init__(self, warehouse, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.warehouse = warehouse
	
	def clean_user_id(self):
		"""
		Validate that the user exists and is in the warehouse
		"""
		user_id = self.cleaned_data.get('user_id')
		if not user_id:
			raise forms.ValidationError("User ID is required.")
		
		try:
			user = User.objects.get(id=user_id)
			if user not in self.warehouse.users.all():
				raise forms.ValidationError("User is not assigned to this warehouse.")
			return user
		except User.DoesNotExist:
			raise forms.ValidationError("User not found.")


