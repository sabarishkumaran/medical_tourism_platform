"""
PayPal Sandbox Test Script
Run: python test_paypal.py
"""
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medtour.settings')

import django
django.setup()

from payments.paypal import get_paypal_access_token, create_paypal_order
from django.conf import settings

print("=" * 60)
print("PayPal Sandbox Integration Test")
print("=" * 60)

print(f"\nClient ID: {settings.PAYPAL_CLIENT_ID[:20]}...")
print(f"Secret: {settings.PAYPAL_SECRET[:10]}...")
print(f"Mode: {settings.PAYPAL_MODE}")

print("\n--- Step 1: Get Access Token ---")
token = get_paypal_access_token()
if token:
    print(f"[OK] SUCCESS: Got access token: {token[:30]}...")
else:
    print("[FAIL] Could not get access token!")
    print("  Your PayPal Client ID or Secret is INVALID.")
    sys.exit(1)

print("\n--- Step 2: Create Test Order ($10.00) ---")
order = create_paypal_order(amount=10.00, description="Test Order from MedTour")
if order:
    print(f"[OK] SUCCESS: Created order ID: {order.get('id')}")
    print(f"  Status: {order.get('status')}")
    for link in order.get('links', []):
        print(f"  Link [{link['rel']}]: {link['href']}")
else:
    print("[FAIL] Could not create order")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED - PayPal integration is working!")
print("=" * 60)
print("\nTo test payments in the browser:")
print("1. Go to https://developer.paypal.com/dashboard/accounts/sandbox")
print("2. Find/create a Personal (buyer) sandbox account")
print("3. Use those sandbox buyer credentials to pay in the PayPal popup")
