from django import template

register = template.Library()


@register.filter
def status_badge(status_value):
	"""Return a colored badge HTML for the given status."""
	status_colors = {
		'active': ('success', 'Active'),
		'maintenance': ('warning', 'In Maintenance'),
		'out_of_service': ('danger', 'Out of Service'),
	}

	color, label = status_colors.get(status_value, ('secondary', status_value))
	return f'<span class="badge rounded-pill bg-{color}">{label}</span>'
