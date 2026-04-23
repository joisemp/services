from django import forms
from config.mixins.form_mixin import BootstrapFormMixin
from .models import Warehouse, Category, Brand, Room, Bucket, Product, Variant, InventorySettings
from core.models import User


class WarehouseForm(BootstrapFormMixin, forms.ModelForm):
	class Meta:
		model = Warehouse
		fields = ['name', 'location']
		labels = {
			'name': 'Warehouse Name',
			'location': 'Location',
		}


class InventorySettingsForm(BootstrapFormMixin, forms.ModelForm):
	class Meta:
		model = InventorySettings
		fields = ['enable_low_stock_alerts', 'low_stock_threshold']
		labels = {
			'enable_low_stock_alerts': 'Enable Low Stock Alerts',
			'low_stock_threshold': 'Low Stock Threshold',
		}
		help_texts = {
			'enable_low_stock_alerts': 'Turn low stock alerting on or off for your organization.',
			'low_stock_threshold': 'Products at or below this quantity are considered low stock.',
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


class BucketForm(BootstrapFormMixin, forms.ModelForm):
	"""
	Form for creating or updating a bucket in a room
	"""
	class Meta:
		model = Bucket
		fields = ['name']
		labels = {
			'name': 'Bucket Name',
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


class MultipleFileInput(forms.ClearableFileInput):
	allow_multiple_selected = True

	def value_from_datadict(self, data, files, name):
		uploads = files.getlist(name)
		if not uploads:
			return None
		return uploads


class MultipleFileField(forms.FileField):
	widget = MultipleFileInput

	def to_python(self, data):
		if data in self.empty_values:
			return None
		if isinstance(data, list):
			return [super(MultipleFileField, self).to_python(item) for item in data]
		return super().to_python(data)

	def validate(self, value):
		if self.required and not value:
			raise forms.ValidationError(self.error_messages['required'], code='required')
		if isinstance(value, list):
			for file_item in value:
				super(MultipleFileField, self).validate(file_item)
			return
		super().validate(value)


class ProductCreateSingleVariantForm(BootstrapFormMixin, forms.Form):
	total_quantity = forms.IntegerField(min_value=0, label='Total Quantity')
	size_name = forms.CharField(max_length=50, label='Size')
	brand = forms.ModelChoiceField(queryset=Brand.objects.none(), required=True, empty_label='Select Brand')
	image_files = MultipleFileField(
		required=False,
		label='Product Images',
		widget=MultipleFileInput(attrs={
			'class': 'form-control',
			'accept': 'image/*',
			'multiple': True,
		}),
		help_text='Optional: upload multiple product images now, or add them later from Manage Images.',
	)

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
	image_files = MultipleFileField(
		required=False,
		label='Variant Images',
		widget=MultipleFileInput(attrs={
			'class': 'form-control',
			'accept': 'image/*',
			'multiple': True,
		}),
		help_text='Optional: upload variant images now, or add them later from Manage Images.',
	)

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


class ProductEditForm(BootstrapFormMixin, forms.Form):
	name = forms.CharField(max_length=255, label='Product Name')
	description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label='Description')
	category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False, empty_label='Select Category')
	unit = forms.ChoiceField(choices=Product._meta.get_field('unit').choices, label='Unit')
	image_files = MultipleFileField(
		required=False,
		label='Add Product Images',
		widget=MultipleFileInput(attrs={
			'class': 'form-control',
			'accept': 'image/*',
			'multiple': True,
		}),
		help_text='Single-variant products only.',
	)

	def __init__(self, *args, **kwargs):
		org = kwargs.pop('org', None)
		super().__init__(*args, **kwargs)

		if org:
			self.fields['category'].queryset = Category.objects.filter(org=org).order_by('name')
		else:
			self.fields['category'].queryset = Category.objects.none()


class ProductTypeConversionForm(BootstrapFormMixin, forms.Form):
	target_type = forms.ChoiceField(choices=Product.TYPE_CHOICES, label='Convert To')
	source_variant = forms.ModelChoiceField(
		queryset=Variant.objects.none(),
		required=False,
		empty_label='Select Source Variant',
	)

	def __init__(self, *args, **kwargs):
		self.product = kwargs.pop('product', None)
		super().__init__(*args, **kwargs)

		if self.product:
			self.fields['source_variant'].queryset = self.product.variants.select_related('brand').order_by('name')
			self.fields['target_type'].choices = [
				(choice_value, choice_label)
				for choice_value, choice_label in Product.TYPE_CHOICES
				if choice_value != self.product.type
			]
		else:
			self.fields['source_variant'].queryset = Variant.objects.none()

	def clean(self):
		cleaned_data = super().clean()
		product = self.product
		target_type = cleaned_data.get('target_type')
		source_variant = cleaned_data.get('source_variant')

		if not product:
			raise forms.ValidationError('Product context is required.')

		if target_type == product.type:
			raise forms.ValidationError('Product is already in the selected type.')

		if product.type == 'MULTI_VARIANT' and target_type == 'SINGLE_VARIANT':
			if not source_variant:
				raise forms.ValidationError('Select a source variant to convert to single variant.')
			if source_variant.product_id != product.id:
				raise forms.ValidationError('Selected variant does not belong to this product.')

		if product.type == 'SINGLE_VARIANT' and target_type == 'MULTI_VARIANT' and source_variant:
			raise forms.ValidationError('Source variant must be empty when converting to multi variant.')

		if product.type == 'MULTI_VARIANT' and target_type == 'MULTI_VARIANT':
			raise forms.ValidationError('Product is already multi variant.')

		if product.type == 'SINGLE_VARIANT' and target_type == 'SINGLE_VARIANT':
			raise forms.ValidationError('Product is already single variant.')

		return cleaned_data


class ProductImageUploadForm(BootstrapFormMixin, forms.Form):
	images = MultipleFileField(
		required=True,
		label='Upload Images',
		widget=MultipleFileInput(attrs={
			'class': 'form-control',
			'accept': 'image/*',
			'multiple': True,
		}),
	)


class StockMovementRecordForm(BootstrapFormMixin, forms.Form):
	reference_code = forms.CharField(
		max_length=32,
		required=False,
		label='Reference Code (Optional)',
		help_text='Leave blank to auto-generate a unique reference code.',
	)
	movement_type = forms.ChoiceField(
		choices=[('INCOMING', 'Incoming'), ('OUTGOING', 'Outgoing')],
	)
	quantity = forms.IntegerField(min_value=1)
	variant = forms.ModelChoiceField(
		queryset=Variant.objects.none(),
		required=False,
		empty_label='Select variant',
	)
	notes = forms.CharField(
		required=False,
		widget=forms.Textarea(attrs={'rows': 2}),
		label='Notes',
	)

	def __init__(self, *args, **kwargs):
		product = kwargs.pop('product', None)
		org = kwargs.pop('org', None)
		warehouse = kwargs.pop('warehouse', None)
		force_movement_type = kwargs.pop('force_movement_type', None)
		super().__init__(*args, **kwargs)

		variants = Variant.objects.none()
		self.product = product
		self.force_movement_type = force_movement_type if force_movement_type in {'INCOMING', 'OUTGOING'} else None

		if product:
			variants = product.variants.all().order_by('name')
		elif org and warehouse:
			variants = Variant.objects.filter(product__org=org, product__warehouse=warehouse).select_related('product').order_by('product__name', 'name')

		self.fields['variant'].queryset = variants

		if product and product.type == 'SINGLE_VARIANT':
			self.fields['variant'].widget = forms.HiddenInput()

		if self.force_movement_type:
			self.fields['movement_type'].initial = self.force_movement_type
			self.fields['movement_type'].widget = forms.HiddenInput()

	def clean(self):
		cleaned_data = super().clean()
		product = self.product
		variant = cleaned_data.get('variant')

		if not product:
			raise forms.ValidationError('Product is required.')

		if product.type == 'MULTI_VARIANT' and not variant:
			raise forms.ValidationError('Multi-variant products require selecting a variant for stock movement.')

		if product.type == 'SINGLE_VARIANT' and variant:
			raise forms.ValidationError('Single-variant products only support product-level movement.')

		if variant and variant.product_id != product.id:
			raise forms.ValidationError('Selected variant does not belong to the selected product.')

		if self.force_movement_type and cleaned_data.get('movement_type') != self.force_movement_type:
			cleaned_data['movement_type'] = self.force_movement_type

		return cleaned_data


class StockMovementCorrectionForm(BootstrapFormMixin, forms.Form):
	reference_code = forms.CharField(
		max_length=32,
		required=False,
		label='Reference Code (Optional)',
		help_text='Leave blank to auto-generate a unique reference code.',
	)
	corrected_quantity = forms.IntegerField(min_value=1, label='Correct Quantity')
	correction_reason = forms.CharField(
		required=False,
		widget=forms.Textarea(attrs={'rows': 2}),
		label='Correction Reason',
	)

	def __init__(self, *args, **kwargs):
		movement = kwargs.pop('movement', None)
		super().__init__(*args, **kwargs)
		self.movement = movement

		if movement:
			self.fields['corrected_quantity'].initial = movement.quantity

	def clean(self):
		cleaned_data = super().clean()
		movement = self.movement

		if not movement:
			raise forms.ValidationError('Stock movement is required.')

		corrected_quantity = cleaned_data.get('corrected_quantity')
		if corrected_quantity is None:
			return cleaned_data

		if corrected_quantity == movement.quantity:
			raise forms.ValidationError('Correct quantity must be different from the original quantity.')

		return cleaned_data


class InventoryReportForm(BootstrapFormMixin, forms.Form):
	REPORT_TYPE_CHOICES = [
		('products', 'Products Report'),
		('stock_movements', 'Stock Movements Report'),
	]

	report_type = forms.ChoiceField(choices=REPORT_TYPE_CHOICES, initial='products')
	date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
	date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
	warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.none(), required=False, empty_label='All Warehouses')
	category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False, empty_label='All Categories')
	brand = forms.ModelChoiceField(queryset=Brand.objects.none(), required=False, empty_label='All Brands')
	product = forms.ModelChoiceField(queryset=Product.all_objects.none(), required=False, empty_label='All Products')
	movement_type = forms.ChoiceField(
		choices=[('', 'All Movement Types')] + list(StockMovementRecordForm.base_fields['movement_type'].choices),
		required=False,
	)
	low_stock_only = forms.BooleanField(required=False)
	include_deleted_products = forms.BooleanField(required=False)

	def __init__(self, *args, **kwargs):
		org = kwargs.pop('org', None)
		super().__init__(*args, **kwargs)
		self.org = org

		if org:
			self.fields['warehouse'].queryset = Warehouse.objects.filter(org=org).order_by('name')
			self.fields['category'].queryset = Category.objects.filter(org=org).order_by('name')
			self.fields['brand'].queryset = Brand.objects.filter(org=org).order_by('name')
			self.fields['product'].queryset = Product.all_objects.filter(org=org).order_by('name')

	def clean(self):
		cleaned_data = super().clean()
		date_from = cleaned_data.get('date_from')
		date_to = cleaned_data.get('date_to')
		report_type = cleaned_data.get('report_type')
		movement_type = cleaned_data.get('movement_type')
		warehouse = cleaned_data.get('warehouse')
		product = cleaned_data.get('product')

		if date_from and date_to and date_from > date_to:
			raise forms.ValidationError('From date must be earlier than or equal to to date.')

		if report_type != 'stock_movements' and movement_type:
			raise forms.ValidationError('Movement type filter is available only for stock movements report.')

		if warehouse and product and product.warehouse_id != warehouse.id:
			raise forms.ValidationError('Selected product does not belong to the selected warehouse.')

		return cleaned_data
