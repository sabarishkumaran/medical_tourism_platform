from django.db import models
from inquiries.models import Inquiry

class Payment(models.Model):
    PAYMENT_TYPES = (
        ('TREATMENT', 'Treatment'),
        ('COMMISSION', 'Commission'),
        ('SUBSCRIPTION', 'Subscription')
    )
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=50)
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='TREATMENT')
    paypal_order_id = models.CharField(max_length=100, null=True, blank=True)
    paypal_payer_id = models.CharField(max_length=100, null=True, blank=True)
    
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.status} - {self.amount} {self.currency}"

class PayPalSubscription(models.Model):
    hospital = models.ForeignKey('hospitals.Hospital', on_delete=models.CASCADE, related_name='paypal_subscriptions')
    paypal_subscription_id = models.CharField(max_length=100, unique=True)
    plan_type = models.CharField(max_length=20)
    status = models.CharField(max_length=50)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.hospital.name} - {self.plan_type} - {self.status}"