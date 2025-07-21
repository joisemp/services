# Currency Configuration for Finance Module
from django.conf import settings
from decimal import Decimal, InvalidOperation
import locale

# Supported currencies
CURRENCIES = {
    'INR': {
        'name': 'Indian Rupee',
        'symbol': '₹',
        'code': 'INR',
        'decimal_places': 2,
        'locale': 'en_IN'
    },
    'USD': {
        'name': 'US Dollar',
        'symbol': '$',
        'code': 'USD',
        'decimal_places': 2,
        'locale': 'en_US'
    },
    'EUR': {
        'name': 'Euro',
        'symbol': '€',
        'code': 'EUR',
        'decimal_places': 2,
        'locale': 'en_EU'
    },
    'GBP': {
        'name': 'British Pound',
        'symbol': '£',
        'code': 'GBP',
        'decimal_places': 2,
        'locale': 'en_GB'
    },
    'JPY': {
        'name': 'Japanese Yen',
        'symbol': '¥',
        'code': 'JPY',
        'decimal_places': 0,
        'locale': 'ja_JP'
    },
}

# Default currency (can be overridden in settings)
DEFAULT_CURRENCY = getattr(settings, 'DEFAULT_CURRENCY', 'INR')

def get_currency_info(currency_code=None):
    """Get currency information"""
    if currency_code is None:
        currency_code = DEFAULT_CURRENCY
    
    return CURRENCIES.get(currency_code, CURRENCIES[DEFAULT_CURRENCY])

def get_currency_symbol(currency_code=None):
    """Get currency symbol"""
    return get_currency_info(currency_code)['symbol']

def get_currency_code(currency_code=None):
    """Get currency code"""
    return get_currency_info(currency_code)['code']

def format_currency(amount, currency_code=None, include_symbol=True):
    """Format amount with currency"""
    if amount is None:
        return "0"
    
    currency_info = get_currency_info(currency_code)
    
    # Convert to Decimal for precise calculation
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError, InvalidOperation):
            return "0.00"
    
    # Round to appropriate decimal places
    decimal_places = currency_info['decimal_places']
    amount = amount.quantize(Decimal('0.01') if decimal_places == 2 else Decimal('1'))
    
    # Format the number
    if decimal_places == 0:
        formatted = f"{amount:,.0f}"
    else:
        formatted = f"{amount:,.{decimal_places}f}"
    
    if include_symbol:
        return f"{currency_info['symbol']} {formatted}"
    else:
        return formatted

def convert_currency(amount, from_currency, to_currency):
    """
    Convert currency (placeholder for future implementation)
    For now, returns the same amount as conversion rates would be fetched from API
    """
    # TODO: Implement actual currency conversion using external API
    # For now, return the same amount
    return amount

class CurrencyMixin:
    """Mixin to add currency support to models"""
    
    def get_currency_code(self):
        """Get currency code for this object"""
        # Try to get from organization settings first
        if hasattr(self, 'org') and self.org:
            return getattr(self.org, 'currency_code', DEFAULT_CURRENCY)
        return DEFAULT_CURRENCY
    
    def get_currency_symbol(self):
        """Get currency symbol for this object"""
        return get_currency_symbol(self.get_currency_code())
    
    def format_amount(self, amount=None, include_symbol=True):
        """Format amount with appropriate currency"""
        if amount is None and hasattr(self, 'amount'):
            amount = self.amount
        
        if amount is None:
            return "0"
            
        return format_currency(amount, self.get_currency_code(), include_symbol)

# Template tags helper functions
def get_template_currency_context(org=None):
    """Get currency context for templates"""
    currency_code = DEFAULT_CURRENCY
    if org and hasattr(org, 'currency_code'):
        currency_code = org.currency_code
    
    currency_info = get_currency_info(currency_code)
    
    return {
        'currency_symbol': currency_info['symbol'],
        'currency_code': currency_info['code'],
        'currency_name': currency_info['name'],
    }
