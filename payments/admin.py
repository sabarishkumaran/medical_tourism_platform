from django.contrib import admin
from .models import Payment, PayPalSubscription
admin.site.register(Payment)
admin.site.register(PayPalSubscription)