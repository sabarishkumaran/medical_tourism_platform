from django.shortcuts import render, redirect, get_object_or_404
from inquiries.models import MedicalDocument, Inquiry, Quote
from .forms import InquiryForm, QuoteForm
from accounts.decorators import hospital_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.paginator import Paginator

@login_required
@hospital_required
def respond_inquiry(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    hospital = request.user.hospital

    # Double check if this hospital should be responding
    if inquiry.hospital and inquiry.hospital != hospital:
        return HttpResponse("Unauthorized", status=403)

    if request.method == "POST":
        form = QuoteForm(request.POST)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.inquiry = inquiry
            quote.hospital = hospital
            quote.save()

            inquiry.status = "QUOTE_SENT"
            inquiry.save()

            return redirect('hospital_dashboard')
    else:
        form = QuoteForm()

    return render(request, "respond_inquiry.html", {
        "form": form,
        "inquiry": inquiry
    })

# Removed @login_required to allow guest submissions
def submit_inquiry(request):
    if request.user.is_authenticated and request.user.role != 'PATIENT':
        return HttpResponse("Unauthorized", status=403)

    from hospitals.models import Hospital

    initial_data = {}
    
    hospital_id = request.GET.get('hospital_id')
    if hospital_id:
        hospital = Hospital.objects.filter(id=hospital_id).first()
        if hospital:
            initial_data['hospital'] = hospital
            initial_data['preferred_country'] = hospital.user.country
            
    package_id = request.GET.get('package_id')
    if package_id:
        from hospitals.models import TreatmentPackage
        package = TreatmentPackage.objects.select_related('treatment', 'hospital').filter(id=package_id).first()
        if package:
            initial_data = {
                'treatment': package.treatment,
                'hospital': package.hospital,
                'package': package,
                'budget': int(package.price),
                'preferred_country': package.hospital.user.country
            }

    hospitals_list = Hospital.objects.filter(status='APPROVED')

    if request.method == "POST":
        form = InquiryForm(request.POST, request.FILES)
        if form.is_valid():
            inquiry = form.save(commit=False)
            
            if request.user.is_authenticated:
                inquiry.patient = request.user
            else:
                # Ghost account creation for guest users
                from accounts.models import User, PatientProfile
                from django.contrib.auth import login
                import secrets
                
                email = request.POST.get('guest_email')
                first_name = request.POST.get('guest_first_name')
                last_name = request.POST.get('guest_last_name')
                
                user = User.objects.filter(email=email).first()
                if not user:
                    user = User.objects.create_user(
                        username=email.split('@')[0] + secrets.token_hex(2),
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        role='PATIENT'
                    )
                    user.set_unusable_password()
                    user.save()
                    PatientProfile.objects.create(user=user)
                
                inquiry.patient = user
                
                # Optionally auto-login the guest so they can see their dashboard immediately
                login(request, user)
                
            inquiry.save()

            files = request.FILES.getlist("documents")
            for file in files:
                MedicalDocument.objects.create(
                    inquiry=inquiry,
                    file=file
                )

            if request.headers.get('HX-Request'):
                return render(request, "partials/inquiry_success.html")

            return redirect("patient_dashboard")
    else:
        form = InquiryForm(initial=initial_data)

    return render(request, "submit_inquiry.html", {"form": form, "hospitals_list": hospitals_list})

@login_required
def inquiry_hub(request):
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)

    from .models import ContactMessage
    from django.contrib import messages

    messages_all = ContactMessage.objects.all().order_by('-created_at')
    
    if request.method == "POST":
        message_id = request.POST.get('message_id')
        try:
            msg = ContactMessage.objects.get(id=message_id)
            msg.is_read = not msg.is_read
            msg.save()
            status_text = "Read" if msg.is_read else "Unread"
        except ContactMessage.DoesNotExist:
            pass
            
        if request.headers.get('HX-Request'):
            # For HTMX POST, we return the updated list
            paginator = Paginator(messages_all, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            return render(request, "partials/inquiry_list.html", {"page_obj": page_obj})
        
        return redirect('inquiry_hub')

    paginator = Paginator(messages_all, 10) # 10 messages per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/inquiry_list.html", {"page_obj": page_obj})
        
    return render(request, "inquiry_hub.html", {"page_obj": page_obj})

@login_required
def inquiry_detail(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    
    # Check permissions: only the patient themselves or staff can see it
    if inquiry.patient != request.user and request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        # Also allow the assigned hospital to see it (though they have respond_inquiry)
        if not (request.user.role == 'HOSPITAL' and inquiry.hospital == request.user.hospital):
            return HttpResponse("Unauthorized", status=403)

    quote = Quote.objects.filter(inquiry=inquiry).first()
    
    return render(request, "inquiry_detail.html", {
        "inquiry": inquiry,
        "quote": quote
    })

@login_required
def patient_inquiries(request):
    if request.user.role != 'PATIENT':
        return HttpResponse("Unauthorized", status=403)
        
    inquiries_list = Inquiry.objects.filter(patient=request.user).order_by('-created_at')
    paginator = Paginator(inquiries_list, 10)
    page_number = request.GET.get('page')
    inquiries = paginator.get_page(page_number)
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/patient_inquiry_list.html", {"inquiries": inquiries})
        
    return render(request, "patient_inquiries.html", {"inquiries": inquiries})

@login_required
def accept_quote(request, inquiry_id):
    if request.user.role != 'PATIENT':
        return HttpResponse("Unauthorized", status=403)
        
    inquiry = get_object_or_404(Inquiry, id=inquiry_id, patient=request.user)
    
    if request.method == "POST":
        quote_id = request.POST.get('quote_id')
        if quote_id:
            quote = get_object_or_404(Quote, id=quote_id, inquiry=inquiry)
            inquiry.hospital = quote.hospital
            
        inquiry.status = "CONFIRMED"
        inquiry.save()
        
        if request.headers.get('HX-Request'):
            return render(request, "partials/quote_accepted_success.html", {"inquiry": inquiry})
            
        from django.contrib import messages
        messages.success(request, "Congratulations! You have confirmed your treatment plan. Our team will contact you for the next steps.")
        return redirect('view_inquiry', inquiry_id=inquiry.id)
        
    return HttpResponse("Method not allowed", status=405)

@login_required
def edit_confirmation(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id, patient=request.user)
    
    if inquiry.status != "CONFIRMED":
        return redirect('view_inquiry', inquiry_id=inquiry.id)
        
    from .forms import ConfirmedInquiryForm
    
    if request.method == 'POST':
        form = ConfirmedInquiryForm(request.POST, instance=inquiry)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return render(request, "partials/quote_accepted_success.html", {"inquiry": inquiry})
            return redirect('view_inquiry', inquiry_id=inquiry.id)
    else:
        form = ConfirmedInquiryForm(instance=inquiry)
        
    return render(request, "edit_confirmation.html", {"form": form, "inquiry": inquiry})

@login_required
def send_payment_link(request, inquiry_id):
    if request.user.role not in ['HOSPITAL', 'ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)
        
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    
    if request.user.role == 'HOSPITAL' and inquiry.hospital != request.user.hospital:
        return HttpResponse("Unauthorized", status=403)
        
    if request.method == "POST":
        inquiry.status = "PAYMENT_LINK_SENT"
        inquiry.save()
        
        from django.contrib import messages
        messages.success(request, f"Payment link successfully sent to {inquiry.patient.get_full_name()}!")
        
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
            
        return redirect('hospital_dashboard')
        
    return HttpResponse("Method not allowed", status=405)

@login_required
def process_payment(request, inquiry_id):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
        
    inquiry = get_object_or_404(Inquiry, id=inquiry_id, patient=request.user)
    
    # In a real application, this would integrate with Stripe or a payment gateway
    # For now, we simulate a successful payment process
    
    import time
    time.sleep(1) # Simulate processing delay
    
    # Process Add-ons
    inquiry.needs_visa_assistance = request.POST.get('visa') == 'on'
    inquiry.needs_travel_booking = request.POST.get('travel') == 'on'
    inquiry.needs_concierge = request.POST.get('concierge') == 'on'
    
    service_fees = 0.00
    if inquiry.needs_visa_assistance:
        service_fees += 99.00
    if inquiry.needs_travel_booking:
        service_fees += 49.00
    if inquiry.needs_concierge:
        service_fees += 199.00
        
    inquiry.service_fees_total = service_fees
    
    # Calculate standard 10% platform commission from hospital
    if inquiry.package:
        inquiry.commission_amount = float(inquiry.package.price) * 0.10
    
    inquiry.status = "COMPLETED"
    inquiry.save()
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/payment_success.html", {"inquiry": inquiry})
        
    from django.contrib import messages
    messages.success(request, "Payment processed successfully! Your treatment is fully booked.")
    return redirect('view_inquiry', inquiry_id=inquiry.id)
