from django.urls import path
from . import views

urlpatterns = [
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    path('subscription/return/', views.subscription_return, name='subscription_return'),
    path('subscription/cancel-url/', views.subscription_cancel_url, name='subscription_cancel_url'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('webhook/paypal/', views.paypal_webhook, name='paypal_webhook'),
]
