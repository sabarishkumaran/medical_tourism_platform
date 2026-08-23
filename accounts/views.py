from hospitals.models import Hospital
from inquiries.models import Inquiry
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from .forms import ProfileForm, RegisterForm
from .models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.core.exceptions import PermissionDenied
from blog.models import BlogPost
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse

def send_otp_html_email(user, otp, subject, recipient_email=None):
    if recipient_email is None:
        recipient_email = user.email
        
    html_message = render_to_string('otp_email_html.html', {
        'user': user,
        'otp': otp
    })
    
    send_mail(
        subject,
        f"Your OTP confirmation code is: {otp}",
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
        html_message=html_message,
        fail_silently=True,
    )

@login_required
def manage_staff(request):
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        raise PermissionDenied("Administrative access required.")
    
    from django.core.paginator import Paginator
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse
    from .forms import StaffInvitationForm
    from .models import StaffInvitation
    
    staff_users_all = User.objects.filter(role__in=['ADMIN', 'COORDINATOR']).order_by('-date_joined')
    
    paginator = Paginator(staff_users_all, 10)
    page_number = request.GET.get('page')
    staff_users = paginator.get_page(page_number)
    
    if request.method == "POST":
        form = StaffInvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': {'email': ['A user with this email already exists.']}})
                messages.error(request, "A user with this email already exists.")
                return redirect('manage_staff')

            invitation = form.save()
            
            invite_link = request.build_absolute_uri(
                reverse('staff_accept_invite', kwargs={'token': invitation.token})
            )
            subject = "Invitation to join Medical Tourism Platform Team"
            message = f"You have been invited to join the platform as a {invitation.get_role_display()}.\n\nPlease click the following link to set up your account. This link is valid for 12 hours:\n{invite_link}"
            
            html_message = render_to_string('staff_invite_email_html.html', {
                'invite_link': invite_link,
                'role': invitation.get_role_display()
            })
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                invitation.delete()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': {'__all__': [f"Failed to send email: {str(e)}"]}})
                messages.error(request, f"Failed to send email: {str(e)}")
                return redirect('manage_staff')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f"Invitation sent successfully to {email}."})
                
            messages.success(request, f"Invitation sent successfully to {email}.")
            return redirect('manage_staff')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, field_errors in form.errors.items():
                    label = field if field == '__all__' else field.replace('_', ' ').title()
                    errors[label] = list(field_errors)
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        form = StaffInvitationForm()
        
    if request.headers.get('HX-Request'):
        return render(request, "partials/staff_list.html", {"staff_users": staff_users})

    return render(request, "manage_staff.html", {
        "staff_users": staff_users,
        "form": form
    })

@login_required
def admin_dashboard(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
    
    from inquiries.models import ContactMessage
    from hospitals.models import Hospital
    from .models import User
    
    from django.db.models import Sum
    
    # Revenue Stats
    commission_revenue = Inquiry.objects.filter(status='COMPLETED').aggregate(total=Sum('commission_amount'))['total'] or 0.00
    
    # Platform volume
    transactions_volume = sum([float(inq.total_amount_paid) for inq in Inquiry.objects.filter(status='COMPLETED')])
    service_fees_revenue = Inquiry.objects.filter(status='COMPLETED').aggregate(total=Sum('service_fees_total'))['total'] or 0.00
    
    from hospitals.models import SubscriptionPlanConfig
    prem_conf = SubscriptionPlanConfig.objects.filter(plan_type='PREMIUM').first()
    elite_conf = SubscriptionPlanConfig.objects.filter(plan_type='ELITE').first()
    prem_price = prem_conf.price if prem_conf else 199.00
    elite_price = elite_conf.price if elite_conf else 499.00

    premium_subs = Hospital.objects.filter(subscription_plan='PREMIUM').count()
    elite_subs = Hospital.objects.filter(subscription_plan='ELITE').count()
    subscription_revenue = float(premium_subs * prem_price) + float(elite_subs * elite_price)
    
    processed_leads = Inquiry.objects.exclude(status='NEW').count()
    lead_revenue = processed_leads * 50  # Flat $50 per qualified lead for calculation
    
    featured_hospitals = Hospital.objects.filter(is_featured=True).count()
    featured_revenue = featured_hospitals * 299  # Flat $299 per featured listing
    
    total_revenue = float(commission_revenue) + float(service_fees_revenue) + subscription_revenue + lead_revenue + featured_revenue
    
    # KPI Stats
    stats = {
        'total_hospitals': Hospital.objects.count(),
        'pending_hospitals': Hospital.objects.filter(status='PENDING').count(),
        'approved_hospitals': Hospital.objects.filter(status='APPROVED').count(),
        'total_inquiries': Inquiry.objects.count(),
        'total_patients': User.objects.filter(role='PATIENT').count(),
        'unread_contacts': ContactMessage.objects.filter(is_read=False).count(),
        'pending_blogs': BlogPost.objects.filter(status='Draft', submitted_for_review=True).count(),
        'revenue': {
            'total': total_revenue,
            'commissions': commission_revenue,
            'services': service_fees_revenue,
            'subscriptions': subscription_revenue,
            'leads': lead_revenue,
            'featured': featured_revenue,
            'total_volume': transactions_volume
        }
    }
    
    # Recent Activity
    recent_inquiries = Inquiry.objects.select_related('patient', 'treatment').order_by('-created_at')[:5]
    recent_hospitals = Hospital.objects.select_related('user').order_by('-user__date_joined')[:5]
    
    patient_emails = User.objects.filter(role='PATIENT').values('email')
    auth_messages = ContactMessage.objects.filter(email__in=patient_emails).order_by('-created_at')[:5]
    guest_messages = ContactMessage.objects.exclude(email__in=patient_emails).order_by('-created_at')[:5]
    
    # Report Drilldown Datasets
    from hospitals.models import Transaction
    
    transactions = Transaction.objects.filter(transaction_type='COMMISSION_FEE').select_related('hospital').order_by('-created_at')
    subscription_hospitals = Hospital.objects.filter(subscription_plan__in=['PREMIUM', 'ELITE']).order_by('-id')
    lead_transactions = Inquiry.objects.exclude(status='NEW').select_related('patient', 'hospital').order_by('-created_at')
    featured_hospitals = Hospital.objects.filter(is_featured=True).order_by('-id')
    
    context = {
        'stats': stats,
        'recent_inquiries': recent_inquiries,
        'recent_hospitals': recent_hospitals,
        'auth_messages': auth_messages,
        'guest_messages': guest_messages,
        'commission_transactions': transactions,
        'subscription_hospitals': subscription_hospitals,
        'lead_transactions': lead_transactions,
        'featured_hospitals': featured_hospitals,
    }
    
    return render(request, "admin_dashboard.html", context)


@login_required
def admin_revenue_commissions(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
    from hospitals.models import Transaction
    from django.db.models import Sum
    transactions = Transaction.objects.filter(transaction_type='COMMISSION_FEE').select_related('hospital').order_by('-created_at')
    total = abs(transactions.aggregate(total=Sum('amount'))['total'] or 0)
    return render(request, 'admin_revenue_commissions.html', {'transactions': transactions, 'total': total})


@login_required
def admin_revenue_subscriptions(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
    from hospitals.models import SubscriptionPlanConfig
    prem_conf = SubscriptionPlanConfig.objects.filter(plan_type='PREMIUM').first()
    elite_conf = SubscriptionPlanConfig.objects.filter(plan_type='ELITE').first()
    prem_price = prem_conf.price if prem_conf else 199.00
    elite_price = elite_conf.price if elite_conf else 499.00

    premium_hospitals = Hospital.objects.filter(subscription_plan='PREMIUM').order_by('-id')
    elite_hospitals = Hospital.objects.filter(subscription_plan='ELITE').order_by('-id')
    total = float(premium_hospitals.count() * prem_price) + float(elite_hospitals.count() * elite_price)
    return render(request, 'admin_revenue_subscriptions.html', {
        'premium_hospitals': premium_hospitals,
        'elite_hospitals': elite_hospitals,
        'total': total,
    })

@login_required
def admin_commission_settlements(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
        
    from django.db.models import Sum, Q
    from hospitals.models import Hospital
    
    # Annotate hospitals with their settled and outstanding commission
    hospitals = Hospital.objects.annotate(
        settled_commission=Sum('inquiry__commission_amount', filter=Q(inquiry__commission_paid=True, inquiry__treatment_completed=True)),
        outstanding_commission=Sum('inquiry__commission_amount', filter=Q(inquiry__commission_paid=False, inquiry__treatment_completed=True))
    )
    
    # Filter to only hospitals that have some commission (settled or outstanding)
    hospitals = [h for h in hospitals if (h.settled_commission or 0) > 0 or (h.outstanding_commission or 0) > 0]
    
    # Calculate totals for the dashboard summary
    total_outstanding = sum([h.outstanding_commission or 0 for h in hospitals])
    total_settled = sum([h.settled_commission or 0 for h in hospitals])
    
    return render(request, 'admin_commission_settlements.html', {
        'hospitals': hospitals,
        'total_outstanding': total_outstanding,
        'total_settled': total_settled
    })

@login_required
def admin_hospital_commission_history(request, hospital_id):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
        
    from hospitals.models import Hospital
    hospital = get_object_or_404(Hospital, id=hospital_id)
    
    # Get all completed treatments for this hospital that have a commission amount
    completed_inquiries = hospital.inquiry_set.filter(treatment_completed=True, commission_amount__gt=0).order_by('-created_at')
    
    # Calculate totals
    settled_commission = sum([inquiry.commission_amount for inquiry in completed_inquiries if inquiry.commission_paid])
    outstanding_commission = sum([inquiry.commission_amount for inquiry in completed_inquiries if not inquiry.commission_paid])
    
    return render(request, 'admin_hospital_commission_history.html', {
        'hospital': hospital,
        'inquiries': completed_inquiries,
        'settled_commission': settled_commission,
        'outstanding_commission': outstanding_commission
    })

@login_required
def admin_revenue_leads(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
    leads = Inquiry.objects.exclude(status='NEW').select_related('patient', 'hospital', 'treatment').order_by('-created_at')
    total = leads.count() * 50
    return render(request, 'admin_revenue_leads.html', {'leads': leads, 'total': total})


@login_required
def admin_revenue_services(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
    from django.db.models import Sum
    inquiries = Inquiry.objects.filter(status='COMPLETED').select_related('patient', 'hospital', 'treatment').order_by('-created_at')
    service_total = inquiries.aggregate(total=Sum('service_fees_total'))['total'] or 0
    featured_count = Hospital.objects.filter(is_featured=True).count()
    featured_total = featured_count * 299
    featured_hospitals = Hospital.objects.filter(is_featured=True).order_by('-id')
    return render(request, 'admin_revenue_services.html', {
        'inquiries': inquiries,
        'service_total': service_total,
        'featured_hospitals': featured_hospitals,
        'featured_total': featured_total,
        'grand_total': float(service_total) + featured_total,
    })

@login_required
def admin_financial_ledger(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
        
    from payments.models import Payment
    from hospitals.models import Transaction
    from django.db.models import Sum, Q
    
    # Patient Payments (Inflows)
    patient_payments = Payment.objects.select_related('inquiry__patient', 'inquiry__hospital', 'inquiry__treatment').order_by('-payment_date')
    total_inflows = patient_payments.filter(status__iexact='completed').aggregate(total=Sum('amount'))['total'] or 0
    
    # Fetch Top Revenue Generating Hospitals
    hospital_revenue = Hospital.objects.annotate(
        total_revenue=Sum('inquiry__commission_amount', filter=Q(inquiry__status='COMPLETED', inquiry__commission_paid=True))
    ).filter(total_revenue__gt=0).order_by('-total_revenue')[:5]

    # Hospital Wallet Activity (Outflows and Deductions)
    transactions = Transaction.objects.select_related('hospital').order_by('-created_at')
    
    # Calculate Payouts (TREATMENT_PAYMENT to hospitals)
    total_payouts = transactions.filter(transaction_type='TREATMENT_PAYMENT').aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate Deductions (COMMISSION_FEE collected from hospital)
    total_deductions = transactions.filter(transaction_type='COMMISSION_FEE').aggregate(total=Sum('amount'))['total'] or 0
    
    return render(request, 'admin_financial_ledger.html', {
        'total_payouts': total_payouts,
        'total_deductions': abs(total_deductions),
        'transactions': transactions,
        'patient_payments': patient_payments,
        'total_inflows': total_inflows,
    })

@login_required
def patient_dashboard(request):
    if request.user.role == 'HOSPITAL':
        return redirect('hospital_dashboard')
    elif request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser:
        return redirect('admin_dashboard')

    from django.core.paginator import Paginator
    inquiries_all = Inquiry.objects.filter(patient=request.user).order_by('-created_at')
    
    # Calculate metrics
    active_count = inquiries_all.filter(status__in=['QUOTE_SENT', 'PAYMENT_LINK_SENT']).count()
    confirmed_count = inquiries_all.filter(status__in=['CONFIRMED', 'COMPLETED']).count()
    
    paginator = Paginator(inquiries_all, 10)
    page_number = request.GET.get('page')
    inquiries = paginator.get_page(page_number)

    if request.headers.get('HX-Request'):
        return render(request, "partials/patient_inquiry_list.html", {
            "inquiries": inquiries
        })

    return render(request, "patient_dashboard.html", {
        "inquiries": inquiries,
        "active_count": active_count,
        "confirmed_count": confirmed_count
    })

def register(request):

    if request.method == "POST":

        form = RegisterForm(request.POST, request.FILES)

        if form.is_valid():

            # Ensure email matches verified email in session
            verified_email = request.session.get('registration_verified_email')
            if not verified_email or verified_email != form.cleaned_data.get('email'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': {'email': ['Please verify your email address first.']}})
                messages.error(request, "Please verify your email address first.")
                return render(request, "register.html", {"form": form})

            user = form.save()
            user.is_email_verified = True
            user.save()

            # Hospital registration logic
            if user.role == 'HOSPITAL':
                from hospitals.models import Hospital
                from django.db.models import Q
                from django.core.mail import send_mail
                from django.conf import settings
                from django.urls import reverse
                
                hospital = Hospital.objects.create(
                    user=user,
                    name=form.cleaned_data.get('hospital_name'),
                    city=form.cleaned_data.get('hospital_city'),
                    address=form.cleaned_data.get('hospital_address'),
                    description=form.cleaned_data.get('hospital_description'),
                    established_year=form.cleaned_data.get('hospital_established_year'),
                    certificate=form.cleaned_data.get('hospital_certificate'),
                    accreditation=form.cleaned_data.get('hospital_accreditation'),
                    status='PENDING'
                )
                
                # Notify admins/superusers and coordinators
                admin_emails = list(User.objects.filter(
                    (Q(role__in=['ADMIN', 'COORDINATOR']) | Q(is_superuser=True)) & Q(is_active=True)
                ).values_list('email', flat=True).distinct())
                if admin_emails:
                    admin_subject = f"New Hospital Sign-up: {hospital.name}"
                    review_link = request.build_absolute_uri(reverse('pending_hospitals'))
                    html_message = render_to_string('admin_hospital_signup_email_html.html', {
                        'hospital': hospital,
                        'review_link': review_link,
                        'is_escalation': False,
                    })
                    send_mail(
                        admin_subject, 
                        f"A new hospital, {hospital.name}, has signed up on the platform and is awaiting approval.", 
                        settings.DEFAULT_FROM_EMAIL, 
                        admin_emails, 
                        html_message=html_message, 
                        fail_silently=True
                    )
                
                # Welcome Email to Hospital
                welcome_subject = "Welcome to MedTour! Application under Review"
                welcome_html = render_to_string('hospital_welcome_email_html.html', {
                    'hospital': hospital
                })
                send_mail(
                    welcome_subject, 
                    f"Welcome to MedTour! Your application for {hospital.name} is currently under review.", 
                    settings.DEFAULT_FROM_EMAIL, 
                    [user.email], 
                    html_message=welcome_html, 
                    fail_silently=True
                )
            
            # Clear session
            del request.session['registration_verified_email']
            
            # Log in automatically after registration
            from django.contrib.auth import login
            login(request, user)

            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                from django.urls import reverse
                return JsonResponse({'success': True, 'redirect': reverse('home')})
            
            messages.success(request, "Registration successful! Welcome to MedTour.")
            return redirect("home")

        else:
            # Return JSON with form errors for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                
                # Map field names to user-friendly labels
                field_labels = {
                    'password1': 'Password',
                    'password2': 'Confirm Password',
                    'hospital_name': 'Hospital Name',
                    'hospital_city': 'City',
                    'hospital_address': 'Complete Address',
                    'hospital_description': 'Description / Specialities',
                    'hospital_established_year': 'Est. Year',
                    'hospital_certificate': 'Accreditation Certificate',
                }
                
                errors = {}
                for field, field_errors in form.errors.items():
                    label = field_labels.get(field, field.replace('_', ' ').title())
                    errors[label] = list(field_errors)
                return JsonResponse({'success': False, 'errors': errors}, status=400)

    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})


def user_login(request):

    if request.method == "POST":

        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():

            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(username=username, password=password)

            if user is not None:
                if not user.is_email_verified:
                    import random
                    from django.core.mail import send_mail
                    from .models import OTPVerification
                    
                    otp = str(random.randint(100000, 999999))
                    OTPVerification.objects.update_or_create(user=user, defaults={'otp_code': otp})
                    
                    send_otp_html_email(user, otp, "Your Medical Tourism Platform Verification Code")
                    request.session['unverified_user_id'] = user.id
                    messages.warning(request, "Please verify your email address. A new code has been sent.")
                    return redirect('verify_otp')

                login(request, user)
                
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)

                if user.role == 'HOSPITAL':
                    return redirect("hospital_dashboard")
                elif user.role in ['ADMIN', 'COORDINATOR']:
                    return redirect("admin_dashboard")
                else:
                    return redirect("patient_dashboard")

    else:
        form = AuthenticationForm()

    return render(request, "login.html", {"form": form})

def user_logout(request):

    logout(request)

    return redirect("home")

@login_required
def profile_view(request):
    user = request.user
    
    # Lazy profile creation to ensure "Medical Info" tab always displays
    if user.role == 'PATIENT':
        from .models import PatientProfile
        PatientProfile.objects.get_or_create(user=user)
    elif user.role == 'HOSPITAL':
        from hospitals.models import Hospital
        # Check if hospital exists, if not create with defaults
        if not Hospital.objects.filter(user=user).exists():
            Hospital.objects.create(
                user=user,
                name=f"{user.username}'s Hospital",
                established_year=2024,
                city="Not Set",
                address="Not Set",
                description="Please update your hospital description."
            )

    if request.method == "POST":
        old_email = user.email
        form = ProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            new_email = form.cleaned_data.get('email')
            form.save()
            
            if new_email and new_email != old_email:
                # Check for verified email in session
                verified_email = request.session.get('profile_verified_email')
                if not verified_email or verified_email != new_email:
                    # Revert email if not verified
                    user.email = old_email
                    user.save(update_fields=['email'])
                    messages.error(request, "Please verify your new email address first.")
                    return redirect('profile')
                
                # Success - clear session key
                del request.session['profile_verified_email']

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Profile updated successfully.', 'redirect': reverse('profile')})
            
            messages.success(request, 'Profile details updated successfully.')
            return redirect('profile')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Map field names to user-friendly labels (generic approach)
                errors = {}
                for field, field_errors in form.errors.items():
                    label = field if field == '__all__' else field.replace('_', ' ').title()
                    errors[label] = list(field_errors)
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        form = ProfileForm(instance=user)

    return render(request, "profile.html", {"form": form})


@login_required
def admin_patients(request):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'COORDINATOR']:
        raise PermissionDenied

    from django.db.models import Count, Q, Prefetch
    from django.core.paginator import Paginator
    from inquiries.models import Inquiry

    # Get all users with PATIENT role and annotate them with total inquiries submitted
    latest_inquiry_prefetch = Prefetch(
        'inquiry_set',
        queryset=Inquiry.objects.select_related('hospital', 'treatment').order_by('-created_at'),
        to_attr='latest_inquiries'
    )
    
    patients_list = User.objects.filter(role='PATIENT').annotate(
        inquiry_count=Count('inquiry')
    ).prefetch_related(latest_inquiry_prefetch)

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status')
    sort = request.GET.get('sort')

    if q:
        patients_list = patients_list.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(inquiry__treatment__name__icontains=q) |
            Q(inquiry__hospital__name__icontains=q)
        ).distinct()

    if status == 'active':
        patients_list = patients_list.filter(inquiry__status__in=['QUOTE_SENT', 'PAYMENT_LINK_SENT']).distinct()
    elif status == 'confirmed':
        patients_list = patients_list.filter(inquiry__status__in=['CONFIRMED', 'COMPLETED']).distinct()
    elif status == 'inactive':
        patients_list = patients_list.filter(inquiry_count=0)

    if sort == 'oldest':
        patients_list = patients_list.order_by('date_joined')
    elif sort == 'inquiries':
        patients_list = patients_list.order_by('-inquiry_count', '-date_joined')
    elif sort == 'name':
        patients_list = patients_list.order_by('first_name', 'last_name', '-date_joined')
    else:
        patients_list = patients_list.order_by('-date_joined')

    paginator = Paginator(patients_list, 15)  # 15 patients per page
    page_number = request.GET.get('page', 1)
    patients = paginator.get_page(page_number)

    context = {
        "patients": patients,
        "q": q,
        "status": status,
        "sort": sort,
    }

    if request.headers.get('HX-Request'):
        return render(request, "partials/patient_grid.html", context)

    return render(request, "admin_patients.html", context)

@login_required
def patient_detail(request, user_id):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'COORDINATOR']:
        raise PermissionDenied("Unauthorized access.")

    from .models import PatientProfile
    from inquiries.models import Inquiry
    
    patient = get_object_or_404(User, id=user_id, role='PATIENT')
    profile, created = PatientProfile.objects.get_or_create(user=patient)
    inquiries = Inquiry.objects.filter(patient=patient).order_by('-created_at')
    
    return render(request, "partials/patient_detail_modal.html", {
        "patient": patient,
        "profile": profile,
        "inquiries": inquiries
    })

@login_required
def delete_account(request):
    if request.method == "POST":
        password = request.POST.get('confirm_password')
        user = request.user
        
        if not password:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Please enter your password to confirm deletion.'}, status=400)
            messages.error(request, "Please enter your password to confirm deletion.")
            return redirect('profile')
            
        if user.check_password(password):
            logout(request)
            user.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect': reverse('home')})
            messages.success(request, "Your account has been permanently deleted.")
            return redirect('home')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Incorrect password. Account deletion failed.'}, status=400)
            messages.error(request, "Incorrect password. Account deletion failed.")
            return redirect('profile')
            
    return redirect('profile')

@login_required
def admin_subscription_settings(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
        
    from hospitals.models import SubscriptionPlanConfig
    
    if request.method == "POST":
        plan_type = request.POST.get('plan_type')
        if plan_type:
            plan = SubscriptionPlanConfig.objects.filter(plan_type=plan_type).first()
            if plan:
                try:
                    plan.price = float(request.POST.get('price', plan.price))
                    plan.max_packages = int(request.POST.get('max_packages', plan.max_packages))
                    plan.commission_free_leads = int(request.POST.get('commission_free_leads', plan.commission_free_leads))
                    plan.ranking_bonus = int(request.POST.get('ranking_bonus', plan.ranking_bonus))
                    plan.display_title = request.POST.get('display_title', plan.display_title)
                    plan.description = request.POST.get('description', plan.description)
                    plan.save()
                    messages.success(request, f"{plan.get_plan_type_display()} settings updated successfully.")
                except ValueError:
                    messages.error(request, "Invalid numeric values provided.")
                    
        return redirect('admin_subscription_settings')
        
    plans = SubscriptionPlanConfig.objects.all().order_by('price')
    return render(request, "admin_subscription_settings.html", {"plans": plans})

def verify_otp(request):
    user_id = request.session.get('unverified_user_id')
    if not user_id:
        return redirect('login')
        
    from .models import User, OTPVerification
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        code = request.POST.get('otp_code', '').strip()
        otp_record = OTPVerification.objects.filter(user=user).first()
        
        if otp_record and otp_record.otp_code == code:
            # Success
            if otp_record.unverified_email:
                user.email = otp_record.unverified_email
                user.is_email_verified = True
                user.save(update_fields=['email', 'is_email_verified'])
                messages.success(request, "Your email address has been successfully updated!")
            else:
                user.is_email_verified = True
                user.save(update_fields=['is_email_verified'])
                messages.success(request, "Your account has been successfully verified!")
                
            otp_record.delete()
            if 'unverified_user_id' in request.session:
                del request.session['unverified_user_id']
            login(request, user)
            
            if user.role == 'HOSPITAL':
                return redirect("hospital_dashboard")
            elif user.role in ['ADMIN', 'COORDINATOR']:
                return redirect("admin_dashboard")
            else:
                return redirect("patient_dashboard")
        else:
            messages.error(request, "Invalid verification code.")
            
    return render(request, "verify_otp.html", {"unverified_user": user})

def resend_otp(request):
    user_id = request.session.get('unverified_user_id')
    if not user_id:
        return redirect('login')
        
    from .models import User, OTPVerification
    import random
    user = get_object_or_404(User, id=user_id)
    
    otp = str(random.randint(100000, 999999))
    OTPVerification.objects.update_or_create(user=user, defaults={'otp_code': otp})
    
    send_otp_html_email(user, otp, "Your NEW Verification Code")
    messages.success(request, "A new verification code has been sent to your email.")
    return redirect('verify_otp')

from django.utils import timezone
from datetime import timedelta

def request_registration_otp(request):
    if request.method == "POST":
        email = request.POST.get('email')
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required.'})
            
        # Check if email is already taken
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'This email is already registered.'})
            
        import random
        otp = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=10)
        
        request.session['registration_otp'] = otp
        request.session['registration_otp_email'] = email
        request.session['registration_otp_expiry'] = expiry.isoformat()
        
        # Send email (using a dummy user object for the helper function)
        class DummyUser:
            def __init__(self, email):
                self.email = email
                self.username = email
        
        send_otp_html_email(DummyUser(email), otp, "Your MedTour Registration Code")
        
        return JsonResponse({'success': True, 'message': 'Verification code sent.', 'expiry': expiry.isoformat()})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})

def verify_registration_otp(request):
    if request.method == "POST":
        otp_input = request.POST.get('otp')
        email_input = request.POST.get('email')
        
        session_otp = request.session.get('registration_otp')
        session_email = request.session.get('registration_otp_email')
        session_expiry_str = request.session.get('registration_otp_expiry')
        
        if not all([session_otp, session_email, session_expiry_str]):
            return JsonResponse({'success': False, 'message': 'No OTP requested.'})
            
        from django.utils import timezone
        expiry = parse_datetime(session_expiry_str)
        
        if timezone.now() > expiry:
            return JsonResponse({'success': False, 'message': 'OTP has expired.'})
            
        if otp_input == session_otp and email_input == session_email:
            request.session['registration_verified_email'] = email_input
            # Clean up
            del request.session['registration_otp']
            del request.session['registration_otp_email']
            del request.session['registration_otp_expiry']
            return JsonResponse({'success': True, 'message': 'Email verified successfully.'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid verification code.'})
            
    return JsonResponse({'success': False, 'message': 'Invalid request.'})

def request_profile_otp(request):
    if request.method == "POST" and request.user.is_authenticated:
        email = request.POST.get('email')
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required.'})
            
        # Check if email is already taken by another user
        if User.objects.filter(email=email).exclude(id=request.user.id).exists():
            return JsonResponse({'success': False, 'message': 'This email is already registered.'})

        import random
        otp = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=10)
        
        request.session['profile_otp'] = otp
        request.session['profile_otp_email'] = email
        request.session['profile_otp_expiry'] = expiry.isoformat()
        
        send_otp_html_email(request.user, otp, "Your MedTour Email Update Code", recipient_email=email)
        
        return JsonResponse({'success': True, 'message': 'Verification code sent.', 'expiry': expiry.isoformat()})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})

def verify_profile_otp(request):
    if request.method == "POST" and request.user.is_authenticated:
        otp_input = request.POST.get('otp')
        email_input = request.POST.get('email')
        
        session_otp = request.session.get('profile_otp')
        session_email = request.session.get('profile_otp_email')
        session_expiry_str = request.session.get('profile_otp_expiry')
        
        if not all([session_otp, session_email, session_expiry_str]):
            return JsonResponse({'success': False, 'message': 'No OTP requested.'})
            
        from django.utils.dateparse import parse_datetime
        expiry = parse_datetime(session_expiry_str)
        
        if timezone.now() > expiry:
            return JsonResponse({'success': False, 'message': 'OTP has expired.'})
            
        if otp_input == session_otp and email_input == session_email:
            request.session['profile_verified_email'] = email_input
            # Clean up
            del request.session['profile_otp']
            del request.session['profile_otp_email']
            del request.session['profile_otp_expiry']
            return JsonResponse({'success': True, 'message': 'Email verified successfully.'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid verification code.'})
            
    return JsonResponse({'success': False, 'message': 'Invalid request.'})

@login_required
def ajax_password_change(request):
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from .forms import CustomPasswordChangeForm
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            return JsonResponse({'success': True, 'message': 'Password changed successfully.'})
        else:
            errors = {}
            for field, field_errors in form.errors.items():
                label = field if field == '__all__' else field.replace('_', ' ').title()
                errors[label] = list(field_errors)
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)

from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import login
from .forms import StaffSignupForm

def staff_accept_invite(request, token):
    from .models import StaffInvitation
    try:
        invitation = StaffInvitation.objects.get(token=token)
    except StaffInvitation.DoesNotExist:
        messages.error(request, "Invalid invitation link.")
        return redirect('login')

    if invitation.is_used:
        messages.error(request, "This invitation link has already been used.")
        return redirect('login')
        
    if timezone.now() > invitation.created_at + timedelta(hours=12):
        messages.error(request, "This invitation link has expired.")
        return redirect('login')

    if request.method == "POST":
        form = StaffSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = invitation.email
            user.role = invitation.role
            user.is_email_verified = True
            user.save()
            
            invitation.is_used = True
            invitation.save()
            
            login(request, user)
            messages.success(request, "Account created successfully. Welcome to the team!")
            return redirect('admin_dashboard')
    else:
        form = StaffSignupForm()
        
    return render(request, 'staff_invite_signup.html', {
        'form': form,
        'email': invitation.email,
        'role': invitation.get_role_display()
    })

@login_required
def admin_global_config(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        messages.error(request, "Access denied. Admin or Coordinator permissions required.")
        return redirect('home')

    from .models import Country
    from hospitals.models import Accreditation

    if request.method == "POST":
        action = request.POST.get('action')
        
        # 1. Add Country
        if action == 'add_country':
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            if name:
                c, created = Country.objects.get_or_create(name=name, defaults={'code': code})
                if created:
                    messages.success(request, f"Country '{name}' added successfully.")
                else:
                    messages.info(request, f"Country '{name}' already exists.")
            else:
                messages.error(request, "Country name is required.")

        # 2. Delete Country
        elif action == 'delete_country':
            country_id = request.POST.get('country_id')
            c = get_object_or_404(Country, id=country_id)
            name = c.name
            c.delete()
            messages.success(request, f"Country '{name}' deleted.")

        # 3. Add Accreditation
        elif action == 'add_accreditation':
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            if name and code:
                acc, created = Accreditation.objects.get_or_create(code=code, defaults={'name': name})
                if created:
                    messages.success(request, f"Accreditation '{name} ({code})' added successfully.")
                else:
                    messages.info(request, f"Accreditation code '{code}' already exists.")
            else:
                messages.error(request, "Both Accreditation code and name are required.")

        # 4. Delete Accreditation
        elif action == 'delete_accreditation':
            acc_id = request.POST.get('accreditation_id')
            acc = get_object_or_404(Accreditation, id=acc_id)
            code = acc.code
            acc.delete()
            messages.success(request, f"Accreditation '{code}' deleted.")

        return redirect('admin_global_config')

    countries = Country.objects.all().order_by('name')
    accreditations = Accreditation.objects.all().order_by('name')

    return render(request, 'admin_global_config.html', {
        'countries': countries,
        'accreditations': accreditations,
    })