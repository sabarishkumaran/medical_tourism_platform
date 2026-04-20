from hospitals.models import Hospital
from inquiries.models import Inquiry
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import ProfileForm, RegisterForm, StaffCreationForm
from .models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from blog.models import BlogPost

@login_required
def manage_staff(request):
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        raise PermissionDenied("Administrative access required.")
    
    from django.core.paginator import Paginator
    staff_users_all = User.objects.filter(role__in=['ADMIN', 'COORDINATOR']).order_by('-date_joined')
    
    paginator = Paginator(staff_users_all, 10)
    page_number = request.GET.get('page')
    staff_users = paginator.get_page(page_number)
    
    if request.method == "POST":
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if request.headers.get('HX-Request'):
                staff_users_all = User.objects.filter(role__in=['ADMIN', 'COORDINATOR']).order_by('-date_joined')
                paginator = Paginator(staff_users_all, 10)
                staff_users = paginator.get_page(1)
                return render(request, "partials/staff_list.html", {"staff_users": staff_users})
            messages.success(request, f"Staff account for {user.username} created successfully.")
            return redirect('manage_staff')
    else:
        form = StaffCreationForm()
        
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
        'pending_blogs': BlogPost.objects.filter(status='Draft').count(),
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
    recent_messages = ContactMessage.objects.order_by('-created_at')[:5]
    
    # Report Drilldown Datasets
    from hospitals.models import WalletTransaction
    commission_transactions = WalletTransaction.objects.filter(transaction_type='COMMISSION_FEE').select_related('hospital').order_by('-created_at')
    subscription_hospitals = Hospital.objects.filter(subscription_plan__in=['PREMIUM', 'ELITE']).order_by('-id')
    lead_transactions = Inquiry.objects.exclude(status='NEW').select_related('patient', 'hospital').order_by('-created_at')
    featured_hospitals = Hospital.objects.filter(is_featured=True).order_by('-id')
    
    context = {
        'stats': stats,
        'recent_inquiries': recent_inquiries,
        'recent_hospitals': recent_hospitals,
        'recent_messages': recent_messages,
        'commission_transactions': commission_transactions,
        'subscription_hospitals': subscription_hospitals,
        'lead_transactions': lead_transactions,
        'featured_hospitals': featured_hospitals,
    }
    
    return render(request, "admin_dashboard.html", context)


@login_required
def admin_revenue_commissions(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")
    from hospitals.models import WalletTransaction
    from django.db.models import Sum
    transactions = WalletTransaction.objects.filter(transaction_type='COMMISSION_FEE').select_related('hospital').order_by('-created_at')
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

            user = form.save()

            # if role is hospital create hospital record
            if user.role == "HOSPITAL":

                Hospital.objects.create(
                    user=user,
                    name=form.cleaned_data["hospital_name"],
                    city=form.cleaned_data["hospital_city"],
                    address=form.cleaned_data["hospital_address"],
                    description=form.cleaned_data["hospital_description"],
                    established_year=form.cleaned_data["hospital_established_year"],
                    certificate=request.FILES.get("hospital_certificate"),
                )

            import random
            from django.core.mail import send_mail
            from django.conf import settings
            from .models import OTPVerification
            
            otp = str(random.randint(100000, 999999))
            OTPVerification.objects.update_or_create(user=user, defaults={'otp_code': otp})
            
            send_mail(
                "Your Medical Tourism Platform Verification Code",
                f"Your OTP confirmation code is: {otp}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            
            request.session['unverified_user_id'] = user.id

            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                from django.urls import reverse
                return JsonResponse({'success': True, 'redirect': reverse('verify_otp')})
            
            from django.urls import reverse
            return redirect("verify_otp")

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
                    from django.conf import settings
                    from .models import OTPVerification
                    
                    otp = str(random.randint(100000, 999999))
                    OTPVerification.objects.update_or_create(user=user, defaults={'otp_code': otp})
                    
                    send_mail(
                        "Your Medical Tourism Platform Verification Code",
                        f"Your OTP confirmation code is: {otp}",
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
                    request.session['unverified_user_id'] = user.id
                    messages.warning(request, "Please verify your email address before logging in.")
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
                # Revert email temporarily
                user.email = old_email
                user.save(update_fields=['email'])
                
                import random
                from django.core.mail import send_mail
                from django.conf import settings
                from .models import OTPVerification
                
                otp = str(random.randint(100000, 999999))
                OTPVerification.objects.update_or_create(user=user, defaults={'otp_code': otp, 'unverified_email': new_email})
                
                send_mail(
                    "Verify your new email address",
                    f"Your OTP confirmation code is: {otp}",
                    settings.DEFAULT_FROM_EMAIL,
                    [new_email],
                    fail_silently=True,
                )
                request.session['unverified_user_id'] = user.id
                messages.warning(request, "Please verify your new email address to complete the update.")
                return redirect('verify_otp')

            messages.success(request, 'Profile details updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=user)

    return render(request, "profile.html", {"form": form})


@login_required
def admin_patients(request):
    if not request.user.is_superuser and request.user.role not in ['ADMIN', 'COORDINATOR']:
        raise PermissionDenied

    from django.db.models import Count
    from django.core.paginator import Paginator

    # Get all users with PATIENT role and annotate them with total inquiries submitted
    patients_list = User.objects.filter(role='PATIENT').annotate(
        inquiry_count=Count('inquiry')
    ).order_by('-date_joined')

    paginator = Paginator(patients_list, 15)  # 15 patients per page
    page_number = request.GET.get('page', 1)
    patients = paginator.get_page(page_number)

    if request.headers.get('HX-Request'):
        return render(request, "partials/patient_grid.html", {"patients": patients})

    return render(request, "admin_patients.html", {"patients": patients})

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
            messages.error(request, "Please enter your password to confirm deletion.")
            return redirect('profile')
            
        if user.check_password(password):
            logout(request)
            user.delete()
            messages.success(request, "Your account has been permanently deleted.")
            return redirect('home')
        else:
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