from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def unit_cost(item):
    """Calculate unit cost from item total and quantity"""
    if not item.estimated_cost or item.quantity <= 0:
        return "0.00"
    unit = item.estimated_cost / item.quantity
    return f"{unit:.2f}"

@register.filter
def get_field_by_id(form, prefix):
    """Helps access form fields with dynamic ids in templates"""
    return prefix
