from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .paypal import create_paypal_subscription, cancel_paypal_subscription, verify_webhook_signature
from .models import PayPalSubscription, Payment
from hospitals.models import Hospital, Transaction
from dateutil.relativedelta import relativedelta
from datetime import date
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def create_subscription(request):
    """Creates a PayPal subscription and returns the approval URL."""
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request'}, status=405)
        
    try:
        data = json.loads(request.body)
        plan_type = data.get('plan_type')
        price = data.get('price')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
    hospital = request.user.hospital
    
    return_url = request.build_absolute_uri(reverse('subscription_return')) + f"?plan_type={plan_type}"
    cancel_url = request.build_absolute_uri(reverse('subscription_cancel_url'))
    
    sub_res = create_paypal_subscription(plan_type, price, return_url, cancel_url)
    
    if sub_res and 'id' in sub_res:
        # Create a pending local record
        PayPalSubscription.objects.create(
            hospital=hospital,
            paypal_subscription_id=sub_res['id'],
            plan_type=plan_type,
            status='APPROVAL_PENDING'
        )
        
        # Find the approval URL
        approval_url = next((link['href'] for link in sub_res.get('links', []) if link['rel'] == 'approve'), None)
        if approval_url:
            return JsonResponse({'approval_url': approval_url})
            
    return JsonResponse({'error': 'Failed to create subscription'}, status=500)

@login_required
def subscription_return(request):
    """Callback after user approves subscription on PayPal."""
    subscription_id = request.GET.get('subscription_id')
    plan_type = request.GET.get('plan_type')
    hospital = request.user.hospital
    
    if subscription_id:
        # Update our DB
        sub = PayPalSubscription.objects.filter(paypal_subscription_id=subscription_id).first()
        if sub:
            sub.status = 'ACTIVE'
            sub.current_period_end = date.today() + relativedelta(months=+1)
            sub.save()
            
            # Update hospital
            hospital.paypal_subscription_id = subscription_id
            hospital.subscription_plan = plan_type
            hospital.subscription_end_date = sub.current_period_end
            hospital.save()
            
            # Record first payment as a transaction
            from hospitals.models import SubscriptionPlanConfig
            plan_config = SubscriptionPlanConfig.objects.filter(plan_type=plan_type).first()
            if plan_config:
                Transaction.objects.create(
                    hospital=hospital,
                    amount=-plan_config.price,
                    transaction_type='SUBSCRIPTION',
                    description=f"PayPal Subscription Started: {plan_type}",
                    paypal_order_id=subscription_id
                )
                
            from django.contrib import messages
            messages.success(request, f"Successfully upgraded to {plan_type} plan!")
            return redirect('hospital_billing')
            
    return redirect('hospital_billing')

@login_required
def subscription_cancel_url(request):
    from django.contrib import messages
    messages.warning(request, "Subscription upgrade cancelled.")
    return redirect('hospital_billing')

@login_required
def cancel_subscription(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request'}, status=405)
        
    hospital = request.user.hospital
    sub_id = hospital.paypal_subscription_id
    
    if sub_id:
        if cancel_paypal_subscription(sub_id):
            sub = PayPalSubscription.objects.filter(paypal_subscription_id=sub_id).first()
            if sub:
                sub.status = 'CANCELLED'
                sub.cancelled_at = date.today()
                sub.save()
            
            # They get to keep their plan until the end date, but auto_renew is off
            hospital.auto_renew = False
            hospital.save()
            
            return JsonResponse({'success': True})
            
    return JsonResponse({'error': 'Failed to cancel'}, status=400)

@csrf_exempt
def paypal_webhook(request):
    """Handle PayPal webhooks for recurring payments."""
    # Note: Signature verification is mocked in paypal.py for now
    try:
        event = json.loads(request.body)
        event_type = event.get('event_type')
        resource = event.get('resource', {})
        
        if event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
            sub_id = resource.get('id')
            sub = PayPalSubscription.objects.filter(paypal_subscription_id=sub_id).first()
            if sub:
                sub.status = 'ACTIVE'
                sub.save()
                
        elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
            sub_id = resource.get('id')
            sub = PayPalSubscription.objects.filter(paypal_subscription_id=sub_id).first()
            if sub:
                sub.status = 'CANCELLED'
                sub.cancelled_at = date.today()
                sub.save()
                sub.hospital.auto_renew = False
                sub.hospital.save()
                
        elif event_type == 'PAYMENT.SALE.COMPLETED':
            # This triggers when a recurring payment is successfully charged
            billing_agreement_id = resource.get('billing_agreement_id')
            amount = resource.get('amount', {}).get('total')
            
            sub = PayPalSubscription.objects.filter(paypal_subscription_id=billing_agreement_id).first()
            if sub:
                # Extend subscription by 1 month
                new_end_date = date.today() + relativedelta(months=+1)
                sub.current_period_end = new_end_date
                sub.save()
                
                sub.hospital.subscription_end_date = new_end_date
                sub.hospital.save()
                
                Transaction.objects.create(
                    hospital=sub.hospital,
                    amount=-float(amount),
                    transaction_type='SUBSCRIPTION',
                    description=f"Automated PayPal Renewal: {sub.plan_type}",
                    paypal_order_id=resource.get('id')
                )
                
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse(status=400)
