from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone

from inventory.models import ProductImage, Variant, VariantImage, StockMovementBatch, StockMovementLine


class ProductCreateWizardSessionMixin:
	wizard_session_key = 'inventory_product_create_wizard'

	def get_wizard_id(self):
		warehouse_slug = self.kwargs.get('slug', '')
		user_id = getattr(self.request.user, 'id', 'anon')
		return f"{warehouse_slug}:{user_id}"

	def get_wizard_store(self):
		return self.request.session.setdefault(self.wizard_session_key, {})

	def get_wizard_data(self):
		store = self.get_wizard_store()
		return store.get(self.get_wizard_id(), {})

	def set_wizard_step_data(self, step, data):
		store = self.get_wizard_store()
		wizard_id = self.get_wizard_id()
		wizard_data = store.get(wizard_id, {})
		wizard_data[step] = data
		store[wizard_id] = wizard_data
		self.request.session[self.wizard_session_key] = store
		self.request.session.modified = True

	def clear_wizard_data(self):
		store = self.get_wizard_store()
		wizard_id = self.get_wizard_id()
		if wizard_id in store:
			del store[wizard_id]
			self.request.session[self.wizard_session_key] = store
			self.request.session.modified = True


def recompute_product_quantities(product):
	if product.type == 'MULTI_VARIANT':
		aggregate = Variant.objects.filter(product=product).aggregate(
			total_incoming=Sum('total_incoming_quantity'),
			total_used=Sum('total_used_quantity'),
		)
		total_incoming = aggregate['total_incoming'] or 0
		total_used = aggregate['total_used'] or 0
		product.total_incoming_quantity = total_incoming
		product.total_used_quantity = total_used
		product.universal_available_quantity = total_incoming - total_used
		product.save(update_fields=['total_incoming_quantity', 'total_used_quantity', 'universal_available_quantity'])
	else:
		product.universal_available_quantity = product.total_incoming_quantity - product.total_used_quantity
		product.save(update_fields=['universal_available_quantity'])

	return product


def validate_product_type_conversion(product, target_type, source_variant=None):
	if target_type not in {'SINGLE_VARIANT', 'MULTI_VARIANT'}:
		raise ValidationError('Invalid target product type.')

	if target_type == product.type:
		raise ValidationError('Product is already in the selected type.')

	if product.type == 'MULTI_VARIANT' and target_type == 'SINGLE_VARIANT':
		if source_variant is None:
			raise ValidationError('Select a source variant to convert to single variant.')
		if source_variant.product_id != product.id:
			raise ValidationError('Selected variant does not belong to this product.')

	if product.type == 'SINGLE_VARIANT' and target_type == 'MULTI_VARIANT' and source_variant is not None:
		raise ValidationError('Source variant is not allowed when converting to multi variant.')


def apply_product_type_conversion(product, target_type, source_variant=None):
	validate_product_type_conversion(product, target_type, source_variant=source_variant)

	if target_type == 'MULTI_VARIANT':
		product.type = 'MULTI_VARIANT'
		product.brand = None
		product.save(update_fields=['type', 'brand'])
		return product

	selected_brand = source_variant.brand
	total_incoming_quantity = source_variant.total_incoming_quantity
	total_used_quantity = source_variant.total_used_quantity

	product.type = 'SINGLE_VARIANT'
	product.brand = selected_brand
	product.total_incoming_quantity = total_incoming_quantity
	product.total_used_quantity = total_used_quantity
	product.universal_available_quantity = total_incoming_quantity - total_used_quantity
	product.save(
		update_fields=[
			'type',
			'brand',
			'total_incoming_quantity',
			'total_used_quantity',
			'universal_available_quantity',
		],
	)

	Variant.objects.filter(product=product).delete()
	recompute_product_quantities(product)

	return product


def apply_stock_movement_line(*, batch, product, variant, movement_type, quantity, notes, actor):
	target = variant if variant else product
	target_type = 'VARIANT' if variant else 'PRODUCT'

	old_total_incoming = target.total_incoming_quantity
	old_total_used = target.total_used_quantity
	old_available = target.universal_available_quantity

	new_total_incoming = old_total_incoming
	new_total_used = old_total_used

	if movement_type == 'INCOMING':
		new_total_incoming += quantity
	elif movement_type == 'OUTGOING':
		if old_available < quantity:
			raise ValidationError(
				f'Outgoing quantity ({quantity}) exceeds available quantity ({old_available}) for {target}.',
			)
		new_total_used += quantity
	else:
		raise ValidationError('Invalid movement type.')

	new_available = new_total_incoming - new_total_used

	target.total_incoming_quantity = new_total_incoming
	target.total_used_quantity = new_total_used
	target.universal_available_quantity = new_available
	target.save(update_fields=['total_incoming_quantity', 'total_used_quantity', 'universal_available_quantity'])

	if variant and product.type == 'MULTI_VARIANT':
		recompute_product_quantities(product)

	return StockMovementLine.objects.create(
		batch=batch,
		org=product.org,
		warehouse=product.warehouse,
		product=product,
		variant=variant,
		target_type=target_type,
		movement_type=movement_type,
		quantity=quantity,
		notes=notes,
		correction_type='ORIGINAL',
		old_total_incoming_quantity=old_total_incoming,
		old_total_used_quantity=old_total_used,
		old_available_quantity=old_available,
		new_total_incoming_quantity=new_total_incoming,
		new_total_used_quantity=new_total_used,
		new_available_quantity=new_available,
		recorded_by=actor,
	)


def apply_stock_movement_correction(*, movement, corrected_quantity, correction_reason, actor, reference_code=''):
	if movement.correction_type != 'ORIGINAL':
		raise ValidationError('Only original stock movements can be corrected.')

	if movement.corrections.exists():
		raise ValidationError('This stock movement was already corrected.')

	if corrected_quantity <= 0:
		raise ValidationError('Correct quantity must be greater than zero.')

	target = movement.variant if movement.variant else movement.product
	target.refresh_from_db(fields=['total_incoming_quantity', 'total_used_quantity', 'universal_available_quantity'])

	old_total_incoming = target.total_incoming_quantity
	old_total_used = target.total_used_quantity
	old_available = target.universal_available_quantity

	new_total_incoming = old_total_incoming
	new_total_used = old_total_used

	quantity_delta = corrected_quantity - movement.quantity
	if movement.movement_type == 'INCOMING':
		new_total_incoming = old_total_incoming + quantity_delta
	elif movement.movement_type == 'OUTGOING':
		new_total_used = old_total_used + quantity_delta
	else:
		raise ValidationError('Invalid movement type.')

	new_available = new_total_incoming - new_total_used

	if new_total_incoming < 0 or new_total_used < 0:
		raise ValidationError('Correction would produce invalid stock totals.')

	if new_available < 0:
		raise ValidationError('Correction would make available quantity negative.')

	target.total_incoming_quantity = new_total_incoming
	target.total_used_quantity = new_total_used
	target.universal_available_quantity = new_available
	target.save(update_fields=['total_incoming_quantity', 'total_used_quantity', 'universal_available_quantity'])

	if movement.variant and movement.product.type == 'MULTI_VARIANT':
		recompute_product_quantities(movement.product)

	batch = StockMovementBatch.objects.create(
		org=movement.org,
		warehouse=movement.warehouse,
		recorded_by=actor,
		reference_code=(reference_code or '').strip(),
		notes=correction_reason,
	)

	return StockMovementLine.objects.create(
		batch=batch,
		org=movement.org,
		warehouse=movement.warehouse,
		product=movement.product,
		variant=movement.variant,
		target_type=movement.target_type,
		movement_type=movement.movement_type,
		quantity=corrected_quantity,
		notes=correction_reason,
		correction_type='CORRECTION',
		corrects_movement=movement,
		corrected_by=actor,
		correction_reason=correction_reason,
		corrected_at=timezone.now(),
		old_total_incoming_quantity=old_total_incoming,
		old_total_used_quantity=old_total_used,
		old_available_quantity=old_available,
		new_total_incoming_quantity=new_total_incoming,
		new_total_used_quantity=new_total_used,
		new_available_quantity=new_available,
		recorded_by=actor,
	)


def create_product_images(product, image_files):
	if not image_files:
		return 0

	current_order = ProductImage.objects.filter(product=product).count()
	created_count = 0
	for offset, image_file in enumerate(image_files):
		ProductImage.objects.create(
			product=product,
			image=image_file,
			display_order=current_order + offset,
		)
		created_count += 1

	return created_count


def create_variant_images(variant, image_files):
	if not image_files:
		return 0

	current_order = VariantImage.objects.filter(variant=variant).count()
	created_count = 0
	for offset, image_file in enumerate(image_files):
		VariantImage.objects.create(
			variant=variant,
			image=image_file,
			display_order=current_order + offset,
		)
		created_count += 1

	return created_count
