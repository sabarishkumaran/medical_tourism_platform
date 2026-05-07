from django.shortcuts import render, redirect, get_object_or_404
from inquiries.models import MedicalDocument, Inquiry, Quote
from .forms import InquiryForm, QuoteForm
from accounts.decorators import hospital_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator

@login_required
@hospital_required
def respond_inquiry(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    hospital = request.user.hospital

    # Double check if this hospital should be responding
    if inquiry.hospital and inquiry.hospital != hospital:
        raise PermissionDenied("This inquiry belongs to a different hospital.")

    # Fetch existing quote if any
    quote = Quote.objects.filter(inquiry=inquiry, hospital=hospital).first()
    quote_already_sent = inquiry.status != "NEW"

    if request.method == "POST":
        if quote_already_sent:
            return redirect('hospital_dashboard')

        form = QuoteForm(request.POST, instance=quote)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.inquiry = inquiry
            quote.hospital = hospital
            quote.save()

            inquiry.status = "QUOTE_SENT"
            inquiry.save()

            return redirect('hospital_dashboard')
    else:
        form = QuoteForm(instance=quote)

    return render(request, "respond_inquiry.html", {
        "form": form,
        "inquiry": inquiry,
        "quote_already_sent": quote_already_sent,
        "quote": quote
    })


@login_required
def submit_inquiry(request):
    if request.user.role != 'PATIENT':
        raise PermissionDenied("Only patients can submit inquiries.")

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
        
        # Filter treatments if hospital is pre-selected
        if hospital_id and 'hospital' in initial_data:
            from hospitals.models import TreatmentPackage
            from treatments.models import Treatment
            treatment_ids = TreatmentPackage.objects.filter(
                hospital=initial_data['hospital']
            ).values_list('treatment_id', flat=True)
            
            form.fields['treatment'].queryset = Treatment.objects.filter(id__in=treatment_ids).order_by('name')

    if request.headers.get('HX-Request') and request.method == "POST":
        return render(request, "submit_inquiry.html", {"form": form, "hospitals_list": hospitals_list})

    return render(request, "submit_inquiry.html", {"form": form, "hospitals_list": hospitals_list})

def load_hospital_treatments(request):
    hospital_id = request.GET.get('hospital')
    if hospital_id:
        from hospitals.models import TreatmentPackage
        from treatments.models import Treatment
        treatment_ids = TreatmentPackage.objects.filter(
            hospital_id=hospital_id
        ).values_list('treatment_id', flat=True)
        treatments = Treatment.objects.filter(id__in=treatment_ids).order_by('name')
    else:
        from treatments.models import Treatment
        treatments = Treatment.objects.all().order_by('name')
        
    return render(request, "partials/treatment_options.html", {"treatments": treatments})

@login_required
def get_treatment_price(request):
    treatment_id = request.GET.get('treatment')
    hospital_id = request.GET.get('hospital')

    from django.http import JsonResponse

    if not treatment_id:
        return JsonResponse({"price": None})

    price = None
    from hospitals.models import TreatmentPackage
    if treatment_id and hospital_id:
        package = TreatmentPackage.objects.filter(treatment_id=treatment_id, hospital_id=hospital_id).first()
        if package:
            price = int(package.price)
    
    if not price and treatment_id:
        # If no specific package exists or no hospital is selected, calculate the average price for the treatment
        from django.db.models import Avg
        avg_price = TreatmentPackage.objects.filter(treatment_id=treatment_id).aggregate(Avg('price'))['price__avg']
        if avg_price:
            price = int(avg_price)
    
    return JsonResponse({"price": price})

@login_required
def inquiry_hub(request):
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        raise PermissionDenied("Unauthorized access.")
        
    inquiries_list = Inquiry.objects.all().order_by('-created_at')
    paginator = Paginator(inquiries_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/admin_inquiry_grid.html", {"page_obj": page_obj})
        
    return render(request, "admin_inquiries_list.html", {"page_obj": page_obj})

@login_required
def contact_messages_hub(request):
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        raise PermissionDenied("Unauthorized access.")

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
        
        return redirect('contact_messages_hub')

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
            raise PermissionDenied("You do not have permission to view this inquiry.")

    quote = Quote.objects.filter(inquiry=inquiry).first()
    
    return render(request, "inquiry_detail.html", {
        "inquiry": inquiry,
        "quote": quote
    })

@login_required
def patient_inquiries(request):
    if request.user.role != 'PATIENT':
        raise PermissionDenied("Unauthorized access.")
        
    inquiries_list = Inquiry.objects.filter(patient=request.user).order_by('-created_at')
    
    status_filter = request.GET.get('status')
    filter_display = "All Inquiries"
    
    if status_filter == 'active':
        inquiries_list = inquiries_list.filter(status__in=['QUOTE_SENT', 'PAYMENT_LINK_SENT'])
        filter_display = "Active Quotes"
    elif status_filter == 'confirmed':
        inquiries_list = inquiries_list.filter(status__in=['CONFIRMED', 'COMPLETED'])
        filter_display = "Confirmed Inquiries"

    paginator = Paginator(inquiries_list, 10)
    page_number = request.GET.get('page')
    inquiries = paginator.get_page(page_number)
    
    from django.utils import timezone
    current_date = timezone.now().date()
    
    context = {
        "inquiries": inquiries,
        "filter_display": filter_display,
        "current_status": status_filter,
        "current_date": current_date,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/patient_inquiry_list.html", context)
        
    return render(request, "patient_inquiries.html", context)

@login_required
def accept_quote(request, inquiry_id):
    if request.user.role != 'PATIENT':
        raise PermissionDenied("Unauthorized access.")
        
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
        raise PermissionDenied("Unauthorized access.")
        
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    
    if request.user.role == 'HOSPITAL' and inquiry.hospital != request.user.hospital:
        raise PermissionDenied("This inquiry belongs to a different hospital.")
        
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
    
    # Calculate standard 5% platform commission from hospital
    base_price = 0
    quote = inquiry.quote_set.order_by('-created_at').first()
    if quote:
        base_price = quote.price
    elif inquiry.package:
        base_price = inquiry.package.price
    else:
        base_price = inquiry.budget or 0
        
    inquiry.commission_amount = float(base_price) * 0.05
    
    # Elite Plan: 0% commission on the first 5 leads/mo
    if inquiry.hospital.subscription_plan == 'ELITE':
        from datetime import date
        current_month_leads = inquiry.hospital.inquiry_set.filter(
            status='COMPLETED',
            created_at__year=date.today().year,
            created_at__month=date.today().month
        ).count()
        
        if current_month_leads < 5:
            inquiry.commission_amount = 0.00
    
    inquiry.status = "COMPLETED"
    inquiry.save()
    
    # Process Automated Commission Deduction from Hospital Lead Wallet
    if inquiry.commission_amount > 0:
        hospital_acc = inquiry.hospital
        from decimal import Decimal
        commission_decimal = Decimal(str(inquiry.commission_amount))
        hospital_acc.wallet_balance -= commission_decimal
        hospital_acc.save()
        from hospitals.models import WalletTransaction
        WalletTransaction.objects.create(
            hospital=hospital_acc,
            amount=-inquiry.commission_amount,
            transaction_type='COMMISSION_FEE',
            description=f"Commission fee deduction for completed Inquiry #{inquiry.id}"
        )
    
    # Save payment details for records
    from payments.models import Payment
    Payment.objects.create(
        inquiry=inquiry,
        amount=inquiry.total_amount_paid,
        currency="USD",
        status="Completed"
    )
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/payment_success.html", {"inquiry": inquiry})
        
    from django.contrib import messages
    messages.success(request, "Payment processed successfully! Your treatment is fully booked.")
    return redirect('view_inquiry', inquiry_id=inquiry.id)

@login_required
@hospital_required
def mark_treatment_completed(request, inquiry_id):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
        
    hospital = request.user.hospital
    inquiry = get_object_or_404(Inquiry, id=inquiry_id, hospital=hospital)
    
    # Must be paid/completed status
    if inquiry.status != "COMPLETED":
        from django.contrib import messages
        messages.error(request, "Cannot mark as completed until payment is settled.")
        return redirect('hospital_manage_inquiries')
        
    from django.utils import timezone
    if inquiry.travel_date and inquiry.travel_date >= timezone.now().date():
        from django.contrib import messages
        messages.error(request, "Cannot mark treatment as completed before the travel date.")
        return redirect('hospital_manage_inquiries')
        
    inquiry.treatment_completed = True
    inquiry.save()
    
    from django.contrib import messages
    messages.success(request, f"Treatment for {inquiry.patient.get_full_name()} marked as completed.")
    return redirect('hospital_manage_inquiries')


@login_required
def submit_review(request, inquiry_id):
    if request.user.role != 'PATIENT':
        raise PermissionDenied("Only patients can submit reviews.")
        
    inquiry = get_object_or_404(Inquiry, id=inquiry_id, patient=request.user)
    
    if not inquiry.treatment_completed:
        raise PermissionDenied("Cannot review until treatment is marked as completed.")
        
    if hasattr(inquiry, 'review') and inquiry.review is not None:
        from django.contrib import messages
        messages.error(request, "You have already submitted a review for this treatment.")
        return redirect('patient_inquiries')
        
    if request.method == "POST":
        rating_str = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()
        
        try:
            rating = int(rating_str)
            if rating < 1 or rating > 5:
                raise ValueError
        except (ValueError, TypeError):
            from django.contrib import messages
            messages.error(request, "Invalid rating submitted.")
            return redirect('patient_inquiries')
            
        from reviews.models import Review
        Review.objects.create(
            inquiry=inquiry,
            hospital=inquiry.hospital,
            patient=request.user,
            rating=rating,
            comment=comment
        )
        
        from django.contrib import messages
        messages.success(request, "Thank you for your feedback! Your review has been submitted.")
        
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
            
        return redirect('patient_inquiries')
        
    return HttpResponse("Method not allowed", status=405)
