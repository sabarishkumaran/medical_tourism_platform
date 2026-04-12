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
    service_fees_revenue = Inquiry.objects.filter(status='COMPLETED').aggregate(total=Sum('service_fees_total'))['total'] or 0.00
    
    premium_subs = Hospital.objects.filter(subscription_plan='PREMIUM').count()
    elite_subs = Hospital.objects.filter(subscription_plan='ELITE').count()
    subscription_revenue = (premium_subs * 199) + (elite_subs * 499)
    
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
            'featured': featured_revenue
        }
    }
    
    # Recent Activity
    recent_inquiries = Inquiry.objects.select_related('patient', 'treatment').order_by('-created_at')[:5]
    recent_hospitals = Hospital.objects.select_related('user').order_by('-user__date_joined')[:5]
    recent_messages = ContactMessage.objects.order_by('-created_at')[:5]
    
    context = {
        'stats': stats,
        'recent_inquiries': recent_inquiries,
        'recent_hospitals': recent_hospitals,
        'recent_messages': recent_messages,
    }
    
    return render(request, "admin_dashboard.html", context)

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

            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': True, 'redirect': '/accounts/login/'})
            
            return redirect("login")

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

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
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