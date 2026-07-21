from django.shortcuts import render, redirect, get_object_or_404
from inquiries.models import MedicalDocument, Inquiry, Quote
from .forms import InquiryForm, QuoteForm
from accounts.decorators import hospital_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.urls import reverse

@login_required
@hospital_required
def respond_inquiry(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id)
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

            # Process dynamic sittings
            from .models import QuoteSitting
            QuoteSitting.objects.filter(quote=quote).delete()
            
            sitting_prices = request.POST.getlist('sitting_price[]')
            sitting_descriptions = request.POST.getlist('sitting_desc[]')
            
            if sitting_prices and sitting_descriptions:
                from decimal import Decimal
                total_price = Decimal('0.00')
                for i, (price, desc) in enumerate(zip(sitting_prices, sitting_descriptions)):
                    if price.strip() and desc.strip():
                        qs = QuoteSitting.objects.create(
                            quote=quote,
                            sitting_number=i+1,
                            description=desc,
                            price=price
                        )
                        total_price += Decimal(price)
                # Update total quote price to sum of sittings if provided
                if total_price > 0:
                    quote.price = total_price
                    quote.save()
            else:
                QuoteSitting.objects.create(
                    quote=quote,
                    sitting_number=1,
                    description="Full Treatment",
                    price=quote.price
                )

            inquiry.status = "QUOTE_SENT"
            inquiry.save()
            
            from .utils import log_inquiry_event
            log_inquiry_event(inquiry, request.user, "Quote Sent", f"Hospital sent a quote for ${quote.price}.")

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
            
            from .utils import log_inquiry_event
            log_inquiry_event(inquiry, request.user if request.user.is_authenticated else None, "Inquiry Submitted", "Patient submitted a new inquiry.")

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
        
    inquiries_list = Inquiry.objects.select_related('patient', 'treatment', 'hospital').all().order_by('-created_at')
    
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status')
    sort = request.GET.get('sort')
    
    if q:
        from django.db.models import Q
        inquiries_list = inquiries_list.filter(
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(patient__username__icontains=q) |
            Q(treatment__name__icontains=q) |
            Q(hospital__name__icontains=q)
        )
        
    if status:
        inquiries_list = inquiries_list.filter(status=status)
        
    if sort == 'oldest':
        inquiries_list = inquiries_list.order_by('created_at')
    elif sort == 'patient_asc':
        inquiries_list = inquiries_list.order_by('patient__first_name', 'patient__last_name', '-created_at')
    elif sort == 'patient_desc':
        inquiries_list = inquiries_list.order_by('-patient__first_name', '-patient__last_name', '-created_at')
    elif sort == 'treatment_asc':
        inquiries_list = inquiries_list.order_by('treatment__name', '-created_at')
    elif sort == 'treatment_desc':
        inquiries_list = inquiries_list.order_by('-treatment__name', '-created_at')
    elif sort == 'hospital_asc':
        inquiries_list = inquiries_list.order_by('hospital__name', '-created_at')
    elif sort == 'hospital_desc':
        inquiries_list = inquiries_list.order_by('-hospital__name', '-created_at')
    elif sort == 'status_asc':
        inquiries_list = inquiries_list.order_by('status', '-created_at')
    elif sort == 'status_desc':
        inquiries_list = inquiries_list.order_by('-status', '-created_at')
    else:
        inquiries_list = inquiries_list.order_by('-created_at')

    paginator = Paginator(inquiries_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "sort": sort,
        "STATUS_CHOICES": Inquiry.STATUS_CHOICES,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/admin_inquiry_grid.html", context)
        
    return render(request, "admin_inquiries_list.html", context)

@login_required
def contact_messages_hub(request):
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        raise PermissionDenied("Unauthorized access.")

    from .models import ContactMessage
    from django.contrib import messages
    from accounts.models import User

    message_type = request.GET.get('type', 'guest')
    patient_emails = User.objects.filter(role='PATIENT').values('email')
    
    if message_type == 'auth':
        messages_all = ContactMessage.objects.filter(email__in=patient_emails)
    else:
        messages_all = ContactMessage.objects.exclude(email__in=patient_emails)
        
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        messages_all = messages_all.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(message__icontains=q)
        )
        
    sort = request.GET.get('sort')
    if sort == 'oldest':
        messages_all = messages_all.order_by('created_at')
    elif sort == 'status_asc':
        messages_all = messages_all.order_by('is_read', '-created_at')
    elif sort == 'status_desc':
        messages_all = messages_all.order_by('-is_read', '-created_at')
    elif sort == 'sender_asc':
        messages_all = messages_all.order_by('first_name', 'last_name', '-created_at')
    elif sort == 'sender_desc':
        messages_all = messages_all.order_by('-first_name', '-last_name', '-created_at')
    else:
        messages_all = messages_all.order_by('-created_at')
    
    if request.method == "POST":
        message_id = request.POST.get('message_id')
        reply_text = request.POST.get('reply_text')
        try:
            msg = ContactMessage.objects.get(id=message_id)
            if reply_text:
                from django.core.mail import send_mail
                from django.conf import settings
                from django.utils import timezone
                from django.template.loader import render_to_string
                
                msg.reply_text = reply_text
                msg.replied_at = timezone.now()
                msg.is_read = True
                msg.save()
                
                html_message = render_to_string('contact_reply_email_html.html', {
                    'first_name': msg.first_name,
                    'original_message': msg.message,
                    'reply_message': reply_text,
                })
                
                send_mail(
                    subject=f"Response to Your Inquiry - MedTour",
                    message=f"Dear {msg.first_name},\n\nThank you for reaching out to us.\n\nYour message:\n\"{msg.message}\"\n\nOur Response:\n{reply_text}\n\nBest regards,\nThe MedTour Team",
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                    recipient_list=[msg.email],
                    fail_silently=True,
                    html_message=html_message,
                )
        except ContactMessage.DoesNotExist:
            pass
            
        if request.headers.get('HX-Request'):
            paginator = Paginator(messages_all, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            return render(request, "partials/inquiry_list.html", {"page_obj": page_obj, "message_type": message_type, "q": q, "sort": sort})
        
        return redirect(f"{reverse('contact_messages_hub')}?type={message_type}")

    paginator = Paginator(messages_all, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj, 
        "message_type": message_type,
        "q": q,
        "sort": sort
    }
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/inquiry_list.html", context)
        
    return render(request, "inquiry_hub.html", context)

@login_required
def inquiry_detail(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id)
    
    # Check permissions: only the patient themselves or staff can see it
    if inquiry.patient != request.user and request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        # Also allow the assigned hospital to see it (though they have respond_inquiry)
        if not (request.user.role == 'HOSPITAL' and inquiry.hospital == request.user.hospital):
            raise PermissionDenied("You do not have permission to view this inquiry.")

    quote = Quote.objects.filter(inquiry=inquiry).first()
    
    # Calculate travel deadlines and remaining days
    from django.utils import timezone
    from datetime import timedelta
    current_date = timezone.now().date()
    
    deadline_date = None
    days_remaining = None
    ticket_upload_allowed = True
    
    if inquiry.travel_date:
        if inquiry.payment_status in ['FULL', 'PARTIAL']:
            # Paid: 1 week (7 days) deadline
            deadline_date = inquiry.travel_date - timedelta(days=7)
        else:
            # Unpaid: 2 weeks (14 days) deadline
            deadline_date = inquiry.travel_date - timedelta(days=14)
            
        days_remaining = (inquiry.travel_date - current_date).days
        # For ticket upload, check how many days remaining before travel date vs the deadline requirement
        required_days = 7 if inquiry.payment_status in ['FULL', 'PARTIAL'] else 14
        if days_remaining < required_days:
            ticket_upload_allowed = False
            
    return render(request, "inquiry_detail.html", {
        "inquiry": inquiry,
        "quote": quote,
        "deadline_date": deadline_date,
        "days_remaining": days_remaining,
        "ticket_upload_allowed": ticket_upload_allowed,
        "current_date": current_date,
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
        
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, patient=request.user)
    
    if request.method == "POST":
        quote_id = request.POST.get('quote_id')
        if quote_id:
            quote = get_object_or_404(Quote, id=quote_id, inquiry=inquiry)
            inquiry.hospital = quote.hospital
            
        inquiry.status = "CONFIRMED"
        inquiry.save()
        
        from .utils import log_inquiry_event
        log_inquiry_event(inquiry, request.user, "Plan Confirmed", "Patient confirmed the treatment plan.")
        
        if request.headers.get('HX-Request'):
            return render(request, "partials/quote_accepted_success.html", {"inquiry": inquiry})
            
        from django.contrib import messages
        messages.success(request, "Congratulations! You have confirmed your treatment plan. Our team will contact you for the next steps.")
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    return HttpResponse("Method not allowed", status=405)

@login_required
def edit_confirmation(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, patient=request.user)
    
    if inquiry.status != "CONFIRMED":
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    from .forms import ConfirmedInquiryForm
    
    if request.method == 'POST':
        form = ConfirmedInquiryForm(request.POST, instance=inquiry)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return render(request, "partials/quote_accepted_success.html", {"inquiry": inquiry})
            return redirect('view_inquiry', inquiry_id=inquiry.uuid)
    else:
        form = ConfirmedInquiryForm(instance=inquiry)
        
    from .models import Quote
    quote = Quote.objects.filter(inquiry=inquiry).order_by('-created_at').first()
        
    return render(request, "edit_confirmation.html", {"form": form, "inquiry": inquiry, "quote": quote})

@login_required
def send_payment_link(request, inquiry_id):
    if request.user.role not in ['HOSPITAL', 'ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        raise PermissionDenied("Unauthorized access.")
        
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id)
    
    if request.user.role == 'HOSPITAL' and inquiry.hospital != request.user.hospital:
        raise PermissionDenied("This inquiry belongs to a different hospital.")
        
    if request.method == "POST":
        inquiry.status = "PAYMENT_LINK_SENT"
        inquiry.save()
        
        from .utils import log_inquiry_event
        log_inquiry_event(inquiry, request.user, "Payment Link Sent", "Hospital requested a deposit payment.")
        
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
        
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, patient=request.user)
    
    payment_choice = request.POST.get('payment_choice', 'unpaid')
    
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
        sitting = quote.sittings.filter(sitting_number=inquiry.current_sitting_number).first()
        base_price = sitting.price if sitting else quote.price
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
    
    from .utils import log_inquiry_event
    
    if payment_choice in ['full', 'partial']:
        import time
        time.sleep(0.5) # Simulate processing delay
        
        # Calculate amount
        if payment_choice == 'full':
            amount_to_pay = float(base_price) + float(service_fees)
            inquiry.payment_status = 'FULL'
        else:
            # Partial payment - deposit is $100 + service fees
            amount_to_pay = 100.00 + float(service_fees)
            inquiry.payment_status = 'PARTIAL'
            
        inquiry.booking_confirmed = True
        inquiry.save()
        
        # Save payment details for records
        from payments.models import Payment
        Payment.objects.create(
            inquiry=inquiry,
            amount=amount_to_pay,
            currency="USD",
            status="Completed"
        )
        log_inquiry_event(inquiry, request.user, "Payment Successful", f"Patient completed {payment_choice} payment of ${amount_to_pay:.2f} successfully via PayPal.")
        msg = f"Payment of ${amount_to_pay:.2f} processed successfully! Your booking is confirmed."
    else:
        # Unpaid option
        inquiry.payment_status = 'UNPAID'
        inquiry.booking_confirmed = False
        inquiry.save()
        log_inquiry_event(inquiry, request.user, "Booking Finalized (Unpaid)", "Patient chose to finalize booking without payment.")
        msg = "Your booking request has been submitted. Please upload your ticket at least 2 weeks before travel to confirm your booking."
        
    if request.headers.get('HX-Request'):
        return render(request, "partials/payment_success.html", {"inquiry": inquiry})
        
    from django.contrib import messages
    messages.success(request, msg)
    return redirect('view_inquiry', inquiry_id=inquiry.uuid)

@login_required
@hospital_required
def mark_treatment_completed(request, inquiry_id):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
        
    hospital = request.user.hospital
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, hospital=hospital)
    
    # Must be completed status (i.e. patient finalized booking)
    if inquiry.status != "COMPLETED":
        from django.contrib import messages
        messages.error(request, "Cannot mark as completed until booking is completed/finalized by the patient.")
        return redirect('hospital_manage_inquiries')
        
    from django.utils import timezone
    if inquiry.travel_date and inquiry.travel_date >= timezone.now().date():
        from django.contrib import messages
        messages.error(request, "Cannot mark treatment as completed before the travel date.")
        return redirect('hospital_manage_inquiries')
        
    # Check if there are more sittings
    quote = Quote.objects.filter(inquiry=inquiry).first()
    if quote:
        total_sittings = quote.sittings.count()
        if inquiry.current_sitting_number < total_sittings:
            inquiry.status = "AWAITING_NEXT_SITTING"
            inquiry.treatment_completed = False
        else:
            inquiry.treatment_completed = True
    else:
        inquiry.treatment_completed = True
        
    inquiry.save()
    
    # Transfer the paid amount (if any) to the hospital
    hospital_acc = inquiry.hospital
    from decimal import Decimal
    total_paid = Decimal(str(inquiry.total_amount_paid))
    
    if total_paid > 0:
        hospital_acc.wallet_balance += total_paid
        from hospitals.models import WalletTransaction
        WalletTransaction.objects.create(
            hospital=hospital_acc,
            amount=total_paid,
            transaction_type='DEPOSIT',
            description=f"Initial Payment Transfer for completed Inquiry #{inquiry.id}"
        )
        hospital_acc.save()
    
    # Send email/link to collect reviews from both parties
    from django.core.mail import send_mail
    from django.conf import settings
    
    # Email to Patient
    patient_review_url = request.build_absolute_uri(reverse('submit_review', args=[inquiry.uuid]))
    send_mail(
        subject="Please rate your experience with " + inquiry.hospital.name,
        message=f"Dear {inquiry.patient.get_full_name() or inquiry.patient.username},\n\nWe hope your treatment was successful. Please click the link below to submit a review of the hospital:\n\n{patient_review_url}\n\nBest regards,\nThe MedTour Team",
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
        recipient_list=[inquiry.patient.email],
        fail_silently=True
    )
    
    # Email to Hospital
    hospital_review_url = request.build_absolute_uri(reverse('submit_patient_review', args=[inquiry.uuid]))
    send_mail(
        subject="Please rate your patient " + (inquiry.patient.get_full_name() or inquiry.patient.username),
        message=f"Dear Partner,\n\nPlease rate and review your experience with the patient {inquiry.patient.get_full_name() or inquiry.patient.username} using this link:\n\n{hospital_review_url}\n\nBest regards,\nThe MedTour Team",
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
        recipient_list=[inquiry.hospital.user.email],
        fail_silently=True
    )
    
    from django.contrib import messages
    messages.success(request, f"Treatment marked as completed. Review collection links sent to both parties.")
    return redirect('hospital_manage_inquiries')

@login_required
def upload_ticket(request, inquiry_id):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
        
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, patient=request.user)
    
    if not inquiry.travel_date:
        from django.contrib import messages
        messages.error(request, "Please set a travel/arrival date before uploading your ticket.")
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    ticket_file = request.FILES.get('ticket_file')
    if not ticket_file:
        from django.contrib import messages
        messages.error(request, "Please select a valid ticket file to upload.")
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    # Check deadline
    from django.utils import timezone
    from datetime import timedelta
    current_date = timezone.now().date()
    travel_date = inquiry.travel_date
    days_remaining = (travel_date - current_date).days
    
    if inquiry.payment_status in ['FULL', 'PARTIAL']:
        # Paid: 1 week (7 days) deadline
        if days_remaining < 7:
            from django.contrib import messages
            messages.error(request, f"Deadline missed. Ticket must be uploaded at least 1 week before travel date. ({days_remaining} days remaining).")
            return redirect('view_inquiry', inquiry_id=inquiry.uuid)
    else:
        # Unpaid: 2 weeks (14 days) deadline
        if days_remaining < 14:
            from django.contrib import messages
            messages.error(request, f"Deadline missed. Unpaid booking ticket must be uploaded at least 2 weeks before travel date. ({days_remaining} days remaining).")
            return redirect('view_inquiry', inquiry_id=inquiry.uuid)
            
    inquiry.ticket_file = ticket_file
    inquiry.ticket_uploaded_at = timezone.now()
    inquiry.booking_confirmed = True  # Officially confirmed now!
    inquiry.save()
    
    from .utils import log_inquiry_event
    log_inquiry_event(inquiry, request.user, "Ticket Uploaded", "Patient uploaded travel ticket. Booking confirmed.")
    
    from django.contrib import messages
    messages.success(request, "Ticket uploaded successfully! Your booking is confirmed.")
    return redirect('view_inquiry', inquiry_id=inquiry.uuid)

@login_required
@hospital_required
def submit_patient_review(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, hospital=request.user.hospital)
    
    if not inquiry.treatment_completed:
        raise PermissionDenied("Cannot submit review until treatment is completed.")
        
    if hasattr(inquiry, 'patient_review') and inquiry.patient_review is not None:
        from django.contrib import messages
        messages.error(request, "You have already submitted a review for this patient.")
        return redirect('hospital_manage_inquiries')
        
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
            return redirect('hospital_manage_inquiries')
            
        from reviews.models import PatientReview
        PatientReview.objects.create(
            inquiry=inquiry,
            hospital=inquiry.hospital,
            patient=inquiry.patient,
            rating=rating,
            comment=comment
        )
        
        from django.contrib import messages
        messages.success(request, "Thank you! Patient review submitted successfully.")
        return redirect('hospital_manage_inquiries')
        
    return render(request, "submit_patient_review.html", {"inquiry": inquiry})

@login_required
def send_commission_link(request, inquiry_id):
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        raise PermissionDenied("Unauthorized access.")
        
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id)
    
    if not inquiry.treatment_completed:
        from django.contrib import messages
        messages.error(request, "Treatment must be completed before sending the commission link.")
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    if request.method == "POST":
        inquiry.commission_payment_link_sent = True
        inquiry.save()
        
        from .utils import log_inquiry_event
        log_inquiry_event(inquiry, request.user, "Commission Link Sent", f"Admin sent commission payment link of ${inquiry.commission_amount} to hospital.")
        
        # Send Email to Hospital
        from django.core.mail import send_mail
        from django.conf import settings
        pay_commission_url = request.build_absolute_uri(reverse('pay_commission', args=[inquiry.uuid]))
        send_mail(
            subject=f"Commission Payment Request for Case #{inquiry.id}",
            message=f"Dear Partner,\n\nTreatment is completed for patient {inquiry.patient.get_full_name() or inquiry.patient.username}. Please pay the platform commission of ${inquiry.commission_amount:.2f} using the link below:\n\n{pay_commission_url}\n\nBest regards,\nThe MedTour Team",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[inquiry.hospital.user.email],
            fail_silently=True
        )
        
        from django.contrib import messages
        messages.success(request, "Commission payment link successfully sent to the hospital.")
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    return HttpResponse("Method not allowed", status=405)

@login_required
def pay_commission(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id)
    
    # Must be hospital assigned or staff
    if request.user.role == 'HOSPITAL' and inquiry.hospital != request.user.hospital:
        raise PermissionDenied("Unauthorized access.")
        
    if request.method == "POST":
        inquiry.commission_paid = True
        inquiry.save()
        
        # Log event
        from .utils import log_inquiry_event
        log_inquiry_event(inquiry, request.user, "Commission Paid", f"Hospital paid the commission of ${inquiry.commission_amount:.2f} via PayPal.")
        
        # Record Wallet Transaction for history (inflow for platform / negative for hospital ledger)
        from hospitals.models import WalletTransaction
        from decimal import Decimal
        WalletTransaction.objects.create(
            hospital=inquiry.hospital,
            amount=-Decimal(str(inquiry.commission_amount)),
            transaction_type='COMMISSION_FEE',
            description=f"PayPal Commission payment for completed Inquiry #{inquiry.id}"
        )
        
        from django.contrib import messages
        messages.success(request, "Commission paid successfully! Thank you.")
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    return render(request, "pay_commission.html", {"inquiry": inquiry})

@login_required
def submit_review(request, inquiry_id):
    if request.user.role != 'PATIENT':
        raise PermissionDenied("Only patients can submit reviews.")
        
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, patient=request.user)
    
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


@login_required
def cancel_and_refund_inquiry(request, inquiry_id):
    if request.user.role != 'PATIENT':
        raise PermissionDenied("Only patients can cancel/refund inquiries.")
        
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, patient=request.user)
    
    # Can only refund if it's paid but not completed
    if inquiry.status == "COMPLETED" and not inquiry.treatment_completed:
        if request.method == "POST":
            inquiry.status = "CANCELLED_REFUNDED"
            inquiry.save()
            
            from .utils import log_inquiry_event
            log_inquiry_event(inquiry, request.user, "Cancelled & Refunded", "Patient cancelled the inquiry and requested a refund.")
            
            # In a real app, integrate with Stripe to refund the 100 dollars here.
            
            from django.contrib import messages
            messages.success(request, "Your treatment has been cancelled and your initial payment has been refunded.")
            return redirect('view_inquiry', inquiry_id=inquiry.uuid)
            
    return HttpResponse("Method not allowed", status=405)

@login_required
def book_next_sitting(request, inquiry_id):
    if request.user.role != 'PATIENT':
        raise PermissionDenied('Only patients can book sittings.')
        
    inquiry = get_object_or_404(Inquiry, uuid=inquiry_id, patient=request.user)
    
    if inquiry.status != 'AWAITING_NEXT_SITTING':
        from django.contrib import messages
        messages.error(request, 'This inquiry is not awaiting a new sitting.')
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    from .models import Quote
    quote = Quote.objects.filter(inquiry=inquiry).first()
    if not quote or inquiry.current_sitting_number >= quote.sittings.count():
        from django.contrib import messages
        messages.error(request, 'No more sittings available.')
        return redirect('view_inquiry', inquiry_id=inquiry.uuid)
        
    inquiry.current_sitting_number += 1
    inquiry.status = 'CONFIRMED'
    inquiry.travel_date = None
    inquiry.save()
    
    from .utils import log_inquiry_event
    log_inquiry_event(inquiry, request.user, "Next Sitting Booked", f"Patient started booking Sitting {inquiry.current_sitting_number}.")
    
    from django.contrib import messages
    messages.success(request, f'You are now booking Sitting {inquiry.current_sitting_number}. Please set your travel date.')
    return redirect('edit_confirmation', inquiry_id=inquiry.uuid)

