from django.urls import path
from . import views

app_name = 'legal'

urlpatterns = [
    path('terms/', views.terms_of_use, name='terms_of_use'),
    path('medical-disclaimer/', views.medical_disclaimer, name='medical_disclaimer'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('patient-agreement/', views.patient_agreement, name='patient_agreement'),
    path('health-data-consent/', views.health_data_consent, name='health_data_consent'),
    path('risk-acknowledgment/', views.risk_acknowledgment, name='risk_acknowledgment'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
    path('complaints/', views.complaints, name='complaints'),
    path('cookie-policy/', views.cookie_policy, name='cookie_policy'),
    path('accessibility/', views.accessibility, name='accessibility'),
    path('acceptable-use/', views.acceptable_use, name='acceptable_use'),
]
