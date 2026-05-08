"""
Django Signals for Fleet Management.
Handles activity tracking, auto-updates, and event-driven workflows.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .middleware import get_current_request_user
from .models import Vehicle, VehicleActivity


def _safe_current_user():
	"""Return the current request user only if it still exists in the database."""
	user = get_current_request_user()
	if user is None:
		return None

	try:
		from core.models import User as CoreUser
		if CoreUser.objects.filter(pk=getattr(user, 'pk', None)).exists():
			return user
	except Exception:
		pass

	return None


def _get_org_for_signal(instance):
	"""Get organization from instance or create default context."""
	if hasattr(instance, 'org'):
		return instance.org
	return None


@receiver(post_save, sender=Vehicle)
def log_vehicle_activity(sender, instance, created, **kwargs):
	"""Log vehicle creation or update."""
	user = _safe_current_user()
	org = _get_org_for_signal(instance)

	if not org:
		return

	if created:
		VehicleActivity.objects.create(
			vehicle=instance,
			org=org,
			action=VehicleActivity.ACTION_CREATED,
			user=user,
			details=f"Vehicle created: {instance.registration_number}",
		)
	else:
		# Generic update tracking (status changes logged separately in view)
		VehicleActivity.objects.create(
			vehicle=instance,
			org=org,
			action=VehicleActivity.ACTION_UPDATED,
			user=user,
			details=f"Vehicle updated: {instance.registration_number}",
		)


@receiver(post_delete, sender=Vehicle)
def log_vehicle_deletion(sender, instance, **kwargs):
	"""Log vehicle deletion."""
	user = _safe_current_user()
	org = _get_org_for_signal(instance)

	if not org:
		return

	VehicleActivity.objects.create(
		vehicle=None,
		vehicle_slug=instance.slug,
		org=org,
		action=VehicleActivity.ACTION_DELETED,
		user=user,
		details=f"Vehicle deleted: {instance.registration_number}",
	)
