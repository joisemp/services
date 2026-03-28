from django.db.models import Sum

from inventory.models import Variant


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
