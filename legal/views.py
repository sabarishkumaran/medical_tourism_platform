from django.shortcuts import render

def terms_of_use(request):
    return render(request, 'legal/terms_of_use.html')

def medical_disclaimer(request):
    return render(request, 'legal/medical_disclaimer.html')

def privacy_policy(request):
    return render(request, 'legal/privacy_policy.html')

def patient_agreement(request):
    return render(request, 'legal/patient_agreement.html')

def health_data_consent(request):
    return render(request, 'legal/health_data_consent.html')

def risk_acknowledgment(request):
    return render(request, 'legal/risk_acknowledgment.html')

def refund_policy(request):
    return render(request, 'legal/refund_cancellation.html')

def complaints(request):
    return render(request, 'legal/complaints.html')

def cookie_policy(request):
    return render(request, 'legal/cookie_policy.html')

def accessibility(request):
    return render(request, 'legal/accessibility.html')

def acceptable_use(request):
    return render(request, 'legal/acceptable_use.html')
