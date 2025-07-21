from django import template
from django.utils.safestring import mark_safe
from decimal import InvalidOperation
from ..currency import format_currency, get_currency_symbol, get_currency_code

register = template.Library()

@register.filter
def currency(value, currency_code=None):
    """Format a value as currency"""
    if value is None:
        return ""
    
    # Handle invalid types gracefully
    try:
        return format_currency(value, currency_code)
    except (ValueError, TypeError, InvalidOperation):
        return "0.00"

@register.filter  
def currency_symbol(org=None):
    """Get currency symbol for organization"""
    if org and hasattr(org, 'currency_code'):
        return get_currency_symbol(org.currency_code)
    return get_currency_symbol()

@register.filter
def currency_code(org=None):
    """Get currency code for organization"""
    if org and hasattr(org, 'currency_code'):
        return get_currency_code(org.currency_code)
    return get_currency_code()

@register.simple_tag
def format_amount(amount, currency_code=None, include_symbol=True):
    """Format amount with currency"""
    if amount is None:
        return ""
    return format_currency(amount, currency_code, include_symbol)

@register.inclusion_tag('finance/partials/currency_display.html')
def currency_display(amount, currency_code=None, css_class=""):
    """Display currency amount with proper formatting"""
    return {
        'amount': amount,
        'formatted_amount': format_currency(amount, currency_code) if amount else "",
        'currency_code': currency_code or get_currency_code(),
        'currency_symbol': get_currency_symbol(currency_code),
        'css_class': css_class
    }

@register.filter
def multiply(value, multiplier):
    """Multiply two values"""
    try:
        return float(value) * float(multiplier)
    except (ValueError, TypeError):
        return 0
