#!/usr/bin/env python
"""
Quick test script to verify currency system is working
Run this from the Django shell: python manage.py shell
"""

from finance.currency import get_currency_info, format_currency, get_template_currency_context
from core.models import Organisation
from decimal import Decimal

def test_currency_system():
    """Test the currency system"""
    print("=== Testing Currency System ===\n")
    
    # Test basic currency info
    print("1. Testing currency info:")
    inr_info = get_currency_info('INR')
    print(f"INR Info: {inr_info}")
    
    usd_info = get_currency_info('USD')
    print(f"USD Info: {usd_info}")
    
    # Test formatting
    print("\n2. Testing currency formatting:")
    amount = Decimal('12345.67')
    
    inr_formatted = format_currency(amount, 'INR')
    print(f"INR: {inr_formatted}")
    
    usd_formatted = format_currency(amount, 'USD')
    print(f"USD: {usd_formatted}")
    
    # Test template context
    print("\n3. Testing template context:")
    try:
        org = Organisation.objects.first()
        if org:
            context = get_template_currency_context(org)
            print(f"Template context: {context}")
        else:
            print("No organisation found")
    except Exception as e:
        print(f"Error getting template context: {e}")
    
    print("\n=== Currency System Test Complete ===")

if __name__ == "__main__":
    test_currency_system()
