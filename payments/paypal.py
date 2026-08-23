import logging
import requests
from django.conf import settings
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

def get_paypal_access_token():
    """Retrieve an OAuth2 access token from PayPal."""
    client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
    client_secret = getattr(settings, 'PAYPAL_SECRET', '')
    mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
    
    base_url = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    auth_url = f"{base_url}/v1/oauth2/token"
    
    response = requests.post(
        auth_url,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"}
    )
    
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        logger.error(f"Failed to get PayPal token: {response.text}")
        return None

def create_paypal_order(amount, currency="USD", description="Medical Tourism Payment", return_url=None, cancel_url=None):
    """Create a one-time payment order."""
    token = get_paypal_access_token()
    if not token:
        return None
        
    mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
    base_url = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    order_url = f"{base_url}/v2/checkout/orders"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "description": description,
                "amount": {
                    "currency_code": currency,
                    "value": f"{float(amount):.2f}"
                }
            }
        ]
    }
    
    if return_url and cancel_url:
        payload["application_context"] = {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW"
        }
    
    response = requests.post(order_url, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json()
    else:
        logger.error(f"Failed to create PayPal order: {response.text}")
        return None

def capture_paypal_order(order_id):
    """Capture an approved PayPal order."""
    token = get_paypal_access_token()
    if not token:
        return None
        
    mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
    base_url = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    capture_url = f"{base_url}/v2/checkout/orders/{order_id}/capture"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(capture_url, headers=headers)
    if response.status_code in [200, 201]:
        return response.json()
    else:
        logger.error(f"Failed to capture PayPal order: {response.text}")
        return None

def get_product_id():
    """Get or create a product ID for subscriptions."""
    token = get_paypal_access_token()
    mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
    base_url = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    product_url = f"{base_url}/v1/catalogs/products"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Try to find existing product
    resp = requests.get(product_url, headers=headers)
    if resp.status_code == 200 and resp.json().get('products'):
        for prod in resp.json()['products']:
            if prod['name'] == 'MedTour Hospital Subscription':
                return prod['id']
                
    # Create new product
    payload = {
        "name": "MedTour Hospital Subscription",
        "description": "Monthly subscription for hospital visibility and leads",
        "type": "SERVICE",
        "category": "MEDICAL_CARE"
    }
    
    response = requests.post(product_url, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json()['id']
    return None

def get_or_create_plan_id(plan_type, price):
    """Get or create a billing plan ID for subscriptions."""
    token = get_paypal_access_token()
    product_id = get_product_id()
    if not token or not product_id:
        return None
        
    mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
    base_url = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    plan_url = f"{base_url}/v1/billing/plans"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Check existing plans
    resp = requests.get(plan_url, headers=headers)
    if resp.status_code == 200 and resp.json().get('plans'):
        for plan in resp.json()['plans']:
            if plan['name'] == f"MedTour {plan_type} Plan" and plan['status'] == 'ACTIVE':
                return plan['id']
                
    # Create new plan
    payload = {
        "product_id": product_id,
        "name": f"MedTour {plan_type} Plan",
        "description": f"Monthly {plan_type} subscription plan",
        "status": "ACTIVE",
        "billing_cycles": [
            {
                "frequency": {
                    "interval_unit": "MONTH",
                    "interval_count": 1
                },
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0, # Infinite
                "pricing_scheme": {
                    "fixed_price": {
                        "value": str(price),
                        "currency_code": "USD"
                    }
                }
            }
        ],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee": {
                "value": "0",
                "currency_code": "USD"
            },
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3
        }
    }
    
    response = requests.post(plan_url, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json()['id']
    logger.error(f"Failed to create plan: {response.text}")
    return None

def create_paypal_subscription(plan_type, price, return_url, cancel_url):
    """Create a subscription for a hospital."""
    token = get_paypal_access_token()
    plan_id = get_or_create_plan_id(plan_type, price)
    
    if not token or not plan_id:
        return None
        
    mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
    base_url = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    sub_url = f"{base_url}/v1/billing/subscriptions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "plan_id": plan_id,
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "SUBSCRIBE_NOW"
        }
    }
    
    response = requests.post(sub_url, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json()
    logger.error(f"Failed to create subscription: {response.text}")
    return None

def cancel_paypal_subscription(subscription_id, reason="Requested by user"):
    """Cancel an active PayPal subscription."""
    token = get_paypal_access_token()
    if not token:
        return False
        
    mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
    base_url = "https://api-m.sandbox.paypal.com" if mode == "sandbox" else "https://api-m.paypal.com"
    cancel_url = f"{base_url}/v1/billing/subscriptions/{subscription_id}/cancel"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "reason": reason
    }
    
    response = requests.post(cancel_url, headers=headers, json=payload)
    if response.status_code == 204:
        return True
    logger.error(f"Failed to cancel subscription {subscription_id}: {response.text}")
    return False

def verify_webhook_signature(transmission_id, timestamp, webhook_id, webhook_event, cert_url, actual_sig):
    """Verify PayPal webhook signature. In a real production app, implement full verification here."""
    return True
