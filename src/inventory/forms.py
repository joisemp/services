from django import forms
from config.mixins.form_mixin import BootstrapFormMixin
from .models import Warehouse, Category, Brand, Room, Bucket, Product, Variant
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


class RoomForm(BootstrapFormMixin, forms.ModelForm):
	"""
	Form for creating or updating a room in a warehouse
	"""
	class Meta:
		model = Room
		fields = ['name']
		labels = {
			'name': 'Room Name',
		}


class ProductCreateStepOneForm(BootstrapFormMixin, forms.Form):
	name = forms.CharField(max_length=255, label='Product Name')
	description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label='Description')
	category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False, empty_label='Select Category')
	unit = forms.ChoiceField(choices=Product._meta.get_field('unit').choices, label='Unit')

	def __init__(self, *args, **kwargs):
		org = kwargs.pop('org', None)
		super().__init__(*args, **kwargs)

		if org:
			self.fields['category'].queryset = Category.objects.filter(org=org).order_by('name')
		else:
			self.fields['category'].queryset = Category.objects.none()


class ProductCreateStepTwoForm(BootstrapFormMixin, forms.Form):
	type = forms.ChoiceField(
		choices=Product.TYPE_CHOICES,
		label='Product Type',
		help_text='Choose single variant for one stock line, or multi variant to create product first and variants later.'
	)


class ProductCreateSingleVariantForm(BootstrapFormMixin, forms.Form):
	total_quantity = forms.IntegerField(min_value=0, label='Total Quantity')
	size_name = forms.CharField(max_length=50, label='Size')
	brand = forms.ModelChoiceField(queryset=Brand.objects.none(), required=True, empty_label='Select Brand')

	def __init__(self, *args, **kwargs):
		org = kwargs.pop('org', None)
		super().__init__(*args, **kwargs)

		if org:
			self.fields['brand'].queryset = Brand.objects.filter(org=org).order_by('name')
		else:
			self.fields['brand'].queryset = Brand.objects.none()


class ProductVariantForm(BootstrapFormMixin, forms.Form):
	name = forms.CharField(max_length=255, label='Variant Name', required=True)
	brand = forms.ModelChoiceField(queryset=Brand.objects.none(), required=False, empty_label='Select Brand')
	size_name = forms.CharField(max_length=50, label='Size', required=False)
	total_incoming_quantity = forms.IntegerField(min_value=0, label='Total Incoming Quantity', initial=0)
	total_used_quantity = forms.IntegerField(min_value=0, label='Total Used Quantity', initial=0)

	def __init__(self, *args, **kwargs):
		org = kwargs.pop('org', None)
		super().__init__(*args, **kwargs)

		if org:
			self.fields['brand'].queryset = Brand.objects.filter(org=org).order_by('name')
		else:
			self.fields['brand'].queryset = Brand.objects.none()

	def clean(self):
		cleaned_data = super().clean()
		total_incoming = cleaned_data.get('total_incoming_quantity')
		total_used = cleaned_data.get('total_used_quantity')

		if total_incoming is not None and total_used is not None and total_used > total_incoming:
			raise forms.ValidationError('Total used quantity cannot be greater than total incoming quantity.')

		return cleaned_data


class ProductAssignRoomForm(BootstrapFormMixin, forms.Form):
	room = forms.ModelChoiceField(queryset=Room.objects.none(), required=False, empty_label='Unassign room')

	def __init__(self, *args, **kwargs):
		warehouse = kwargs.pop('warehouse', None)
		super().__init__(*args, **kwargs)

		if warehouse:
			self.fields['room'].queryset = Room.objects.filter(warehouse=warehouse).order_by('name')
		else:
			self.fields['room'].queryset = Room.objects.none()


class ProductAssignBucketForm(BootstrapFormMixin, forms.Form):
	bucket = forms.ModelChoiceField(queryset=Bucket.objects.none(), required=False, empty_label='Unassign bucket')

	def __init__(self, *args, **kwargs):
		warehouse = kwargs.pop('warehouse', None)
		room = kwargs.pop('room', None)
		super().__init__(*args, **kwargs)

		if room:
			self.fields['bucket'].queryset = Bucket.objects.filter(room=room).order_by('name')
		elif warehouse:
			self.fields['bucket'].queryset = Bucket.objects.filter(room__warehouse=warehouse).order_by('room__name', 'name')
		else:
			self.fields['bucket'].queryset = Bucket.objects.none()


class ProductAssignCategoryForm(BootstrapFormMixin, forms.Form):
	category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False, empty_label='Unassign category')

	def __init__(self, *args, **kwargs):
		org = kwargs.pop('org', None)
		super().__init__(*args, **kwargs)

		if org:
			self.fields['category'].queryset = Category.objects.filter(org=org).order_by('name')
		else:
			self.fields['category'].queryset = Category.objects.none()


class ProductAssignBrandForm(BootstrapFormMixin, forms.Form):
	brand = forms.ModelChoiceField(queryset=Brand.objects.none(), required=False, empty_label='Unassign brand')

	def __init__(self, *args, **kwargs):
		org = kwargs.pop('org', None)
		super().__init__(*args, **kwargs)

		if org:
			self.fields['brand'].queryset = Brand.objects.filter(org=org).order_by('name')
		else:
			self.fields['brand'].queryset = Brand.objects.none()
