from datetime import datetime

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.core.exceptions import PermissionDenied

from accounts.decorators import hospital_required
from appointments.models import Appointment
from hospitals.forms import DoctorForm, TreatmentPackageForm
from inquiries.models import Inquiry
from .models import Hospital, Doctor, TreatmentPackage, HospitalImage
from django.contrib.auth.decorators import login_required


def hospital_detail(request, id):

    hospital = get_object_or_404(Hospital, id=id, status__iexact="APPROVED")

    doctors = Doctor.objects.filter(hospital=hospital)

    treatments = TreatmentPackage.objects.filter(hospital=hospital)

    context = {
        "hospital": hospital,
        "doctors": doctors,
        "treatments": treatments
    }

    return render(request, "hospital_detail.html", context)


@login_required
def pending_hospitals(request):
    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied
        
    status_filter = request.GET.get('status', 'ALL')
    
    if status_filter == 'ALL':
        hospitals_all = Hospital.objects.all().order_by('-user__date_joined')
    else:
        hospitals_all = Hospital.objects.filter(status=status_filter).order_by('-user__date_joined')
        
    from django.core.paginator import Paginator
    
    paginator = Paginator(hospitals_all, 10)
    page_number = request.GET.get('page')
    hospitals = paginator.get_page(page_number)
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/pending_hospital_grid.html", {"hospitals": hospitals, "status_filter": status_filter})
        
    return render(request, "pending_hospitals.html", {"hospitals": hospitals, "status_filter": status_filter})

@hospital_required
def upload_hospital_photos(request):
    hospital = request.user.hospital
    if request.method == "POST":
        images = request.FILES.getlist('photos')
        for img in images:
            HospitalImage.objects.create(hospital=hospital, image=img)
        messages.success(request, 'Hospital photos uploaded successfully.')
        return redirect('hospital_dashboard')
    
    return render(request, "upload_hospital_photos.html", {"hospital": hospital})

@login_required
def review_hospital(request, hospital_id):

    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        return HttpResponse("Unauthorized")

    hospital = get_object_or_404(Hospital, id=hospital_id)

    return render(request, "review_hospital.html", {
        "hospital": hospital,
        "accreditation_choices": Hospital.ACCREDITATION_CHOICES,
    })

@login_required
def approve_hospital(request, hospital_id):

    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        return HttpResponse("Unauthorized")

    if request.method != "POST":
        return redirect("review_hospital", hospital_id=hospital_id)

    hospital = get_object_or_404(Hospital, id=hospital_id)

    accreditation = request.POST.get("accreditation", "")
    hospital.accreditation = accreditation
    hospital.status = "APPROVED"
    hospital.save()

    if request.headers.get('HX-Request'):
        from django.core.paginator import Paginator
        hospitals_all = Hospital.objects.filter(status='PENDING').order_by('-user__date_joined')
        paginator = Paginator(hospitals_all, 10)
        page_number = request.GET.get('page', 1)
        hospitals = paginator.get_page(page_number)
        return render(request, "partials/pending_hospital_grid.html", {"hospitals": hospitals})

    return redirect("pending_hospitals")

@login_required
def reject_hospital(request, hospital_id):

    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        return HttpResponse("Unauthorized")

    if request.method != "POST":
        return redirect("review_hospital", hospital_id=hospital_id)

    hospital = get_object_or_404(Hospital, id=hospital_id)

    hospital.status = "REJECTED"
    hospital.save()

    if request.headers.get('HX-Request'):
        from django.core.paginator import Paginator
        hospitals_all = Hospital.objects.filter(status='PENDING').order_by('-user__date_joined')
        paginator = Paginator(hospitals_all, 10)
        page_number = request.GET.get('page', 1)
        hospitals = paginator.get_page(page_number)
        return render(request, "partials/pending_hospital_grid.html", {"hospitals": hospitals})

    return redirect("pending_hospitals")

@hospital_required
def hospital_dashboard(request):
    hospital_user = request.user
    hospital = hospital_user.hospital  # your logged-in hospital
    
    if hospital.status != 'APPROVED':
        return render(request, "hospital_pending_approval.html", {"hospital": hospital})
    doctors = Doctor.objects.filter(hospital=hospital)
    packages = TreatmentPackage.objects.filter(hospital=hospital)

    # Get all treatments offered by this hospital
    hospital_treatment_ids = TreatmentPackage.objects.filter(
        hospital=hospital
    ).values_list('treatment_id', flat=True)

    # Get inquiries for this hospital (direct or via offered treatments)
    from django.db.models import Q
    hospital_inquiries = Inquiry.objects.filter(
        Q(hospital=hospital) | Q(treatment_id__in=hospital_treatment_ids)
    ).distinct()
    total_inquiries = hospital_inquiries.count()

    # Pending approvals (status = 'NEW')
    pending_approvals = hospital_inquiries.filter(status='NEW').count()
    
    # Pending quotes (status = 'QUOTE_SENT')
    pending_quotes = hospital_inquiries.filter(status='QUOTE_SENT').count()

    # Recent inquiries (last 10)
    recent_inquiries = hospital_inquiries.order_by('-created_at')[:10]

    # Upcoming appointments (assuming Appointment links to Inquiry)
    upcoming_appointments = Appointment.objects.filter(
        inquiry__in=hospital_inquiries,
        appointment_date__gte=datetime.today().date()  # only future appointments
    ).count()

    # Calculate Estimated Revenue
    from django.db.models import Sum
    revenue_sum = hospital_inquiries.filter(
        status__in=['CONFIRMED', 'PAYMENT_LINK_SENT', 'COMPLETED']
    ).aggregate(total=Sum('package__price'))['total'] or 0.0
    
    if revenue_sum >= 1000:
        estimated_revenue = f"${revenue_sum / 1000:.1f}k"
    else:
        estimated_revenue = f"${revenue_sum:.0f}"

    context = {
        "total_inquiries": total_inquiries,
        "pending_approvals": pending_approvals,
        "pending_quotes": pending_quotes,
        "recent_inquiries": recent_inquiries,
        "upcoming_appointments": upcoming_appointments,
        "estimated_revenue": estimated_revenue,
        "doctors": doctors,
        "packages": packages,
    }

    return render(request, "hospital_dashboard.html", context)

@hospital_required
def manage_doctors(request):
    hospital = request.user.hospital
    from django.core.paginator import Paginator
    doctors_all = Doctor.objects.filter(hospital=hospital).order_by('name')
    
    paginator = Paginator(doctors_all, 12)
    page_number = request.GET.get('page')
    doctors = paginator.get_page(page_number)
    
    return render(request, "manage_doctors.html", {
        "hospital": hospital,
        "doctors": doctors
    })

@hospital_required
def add_doctor(request):
    if request.method == "POST":
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            doctor = form.save(commit=False)
            doctor.hospital = request.user.hospital
            doctor.save()
            return redirect('hospital_dashboard')
    else:
        form = DoctorForm()
    return render(request, "add_doctor.html", {"form": form})

@hospital_required
def add_treatment_package(request):
    if request.method == "POST":
        form = TreatmentPackageForm(request.POST, hospital=request.user.hospital)
        if form.is_valid():
            form.save()
            return redirect('hospital_dashboard')
    else:
        form = TreatmentPackageForm(hospital=request.user.hospital)
    return render(request, "add_treatment_package.html", {"form": form})

@hospital_required
def edit_treatment_package(request, package_id):
    package = get_object_or_404(TreatmentPackage, id=package_id)
    if package.hospital != request.user.hospital:
        return HttpResponse("Unauthorized", status=403)
        
    if request.method == "POST":
        form = TreatmentPackageForm(request.POST, request.FILES, instance=package, hospital=request.user.hospital)
        if form.is_valid():
            form.save()
            return redirect('hospital_dashboard')
    else:
        form = TreatmentPackageForm(instance=package, hospital=request.user.hospital)
        
    return render(request, "edit_treatment_package.html", {"form": form, "package": package})

@hospital_required
def edit_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if doctor.hospital != request.user.hospital:
        return HttpResponse("Unauthorized")
    if request.method == "POST":
        form = DoctorForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            return redirect('hospital_dashboard')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, "edit_doctor.html", {"form": form, "doctor": doctor})

@hospital_required
def delete_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if doctor.hospital != request.user.hospital:
        return HttpResponse("Unauthorized")
    if request.method == "POST":
        doctor.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse("")  # HTMX will remove the target
    return redirect('hospital_dashboard')

def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    return render(request, "doctor_detail.html", {"doctor": doctor})

@hospital_required
def delete_treatment_package(request, package_id):
    if request.method == "POST":
        package = get_object_or_404(TreatmentPackage, id=package_id)
        if package.hospital != request.user.hospital:
            return HttpResponse("Unauthorized")
        package.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse("")  # HTMX will remove the target
    return redirect('hospital_dashboard')

def hospital_list(request):
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    query = request.GET.get('q', '')
    country = request.GET.get('country', '')
    accreditation = request.GET.get('accreditation', '')
    
    hospitals_all = Hospital.objects.filter(status='APPROVED').order_by('name')
    
    if query:
        hospitals_all = hospitals_all.filter(
            Q(name__icontains=query) | 
            Q(city__icontains=query) | 
            Q(user__country__icontains=query)
        )
    
    if country:
        hospitals_all = hospitals_all.filter(user__country__icontains=country)
        
    if accreditation:
        hospitals_all = hospitals_all.filter(accreditation__iexact=accreditation)
        
    paginator = Paginator(hospitals_all, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get distinct countries for filter dropdown
    countries = Hospital.objects.filter(status='APPROVED').values_list('user__country', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'countries': countries,
        'query': query,
        'current_country': country,
        'current_accreditation': accreditation,
        'accreditation_options': Hospital.ACCREDITATION_CHOICES,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/hospital_grid.html", context)
        
    return render(request, "hospital_list.html", context)
