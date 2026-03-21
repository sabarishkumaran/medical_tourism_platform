from hospitals.models import Hospital
from inquiries.models import Inquiry
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import ProfileForm, RegisterForm, StaffCreationForm
from .models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

@login_required
def manage_staff(request):
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)
    
    from django.core.paginator import Paginator
    staff_users_all = User.objects.filter(role__in=['ADMIN', 'COORDINATOR']).order_by('-date_joined')
    
    paginator = Paginator(staff_users_all, 10)
    page_number = request.GET.get('page')
    staff_users = paginator.get_page(page_number)
    
    if request.method == "POST":
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Staff account for {user.username} created successfully.")
            return redirect('manage_staff')
    else:
        form = StaffCreationForm()
        
    return render(request, "manage_staff.html", {
        "staff_users": staff_users,
        "form": form
    })

@login_required
def admin_dashboard(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        return HttpResponse("Unauthorized", status=403)
    
    from inquiries.models import ContactMessage
    from hospitals.models import Hospital
    from .models import User
    
    # KPI Stats
    stats = {
        'total_hospitals': Hospital.objects.count(),
        'pending_hospitals': Hospital.objects.filter(status='PENDING').count(),
        'approved_hospitals': Hospital.objects.filter(status='APPROVED').count(),
        'total_inquiries': Inquiry.objects.count(),
        'total_patients': User.objects.filter(role='PATIENT').count(),
        'unread_contacts': ContactMessage.objects.filter(is_read=False).count(),
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
    from django.core.paginator import Paginator
    inquiries_all = Inquiry.objects.filter(patient=request.user).order_by('-created_at')
    
    paginator = Paginator(inquiries_all, 10)
    page_number = request.GET.get('page')
    inquiries = paginator.get_page(page_number)

    return render(request, "patient_dashboard.html", {
        "inquiries": inquiries
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

            return redirect("login")

            # login(request, user)

            # return redirect("patient_dashboard")

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