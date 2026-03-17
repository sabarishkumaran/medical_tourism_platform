from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404

from accounts.decorators import hospital_required
from appointments.models import Appointment
from hospitals.forms import DoctorForm, TreatmentPackageForm
from inquiries.models import Inquiry
from .models import Hospital, Doctor, TreatmentPackage
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

    if request.user.role not in ['ADMIN', 'COORDINATOR']:
        return HttpResponse("Unauthorized")

    hospitals = Hospital.objects.filter(status="PENDING")

    return render(request, "pending_hospitals.html", {"hospitals": hospitals})

@login_required
def review_hospital(request, hospital_id):

    if request.user.role not in ['ADMIN', 'COORDINATOR']:
        return HttpResponse("Unauthorized")

    hospital = get_object_or_404(Hospital, id=hospital_id)

    return render(request, "review_hospital.html", {
        "hospital": hospital,
        "accreditation_choices": Hospital.ACCREDITATION_CHOICES,
    })

@login_required
def approve_hospital(request, hospital_id):

    if request.user.role not in ['ADMIN', 'COORDINATOR']:
        return HttpResponse("Unauthorized")

    if request.method != "POST":
        return redirect("review_hospital", hospital_id=hospital_id)

    hospital = get_object_or_404(Hospital, id=hospital_id)

    accreditation = request.POST.get("accreditation", "")
    hospital.accreditation = accreditation
    hospital.status = "APPROVED"
    hospital.save()

    return redirect("pending_hospitals")

@login_required
def reject_hospital(request, hospital_id):

    if request.user.role not in ['ADMIN', 'COORDINATOR']:
        return HttpResponse("Unauthorized")

    if request.method != "POST":
        return redirect("review_hospital", hospital_id=hospital_id)

    hospital = get_object_or_404(Hospital, id=hospital_id)

    hospital.status = "REJECTED"
    hospital.save()

    return redirect("pending_hospitals")

@hospital_required
def hospital_dashboard(request):
    hospital_user = request.user
    hospital = hospital_user.hospital  # your logged-in hospital
    doctors = Doctor.objects.filter(hospital=hospital)
    packages = TreatmentPackage.objects.filter(hospital=hospital)

    # Get all treatments offered by this hospital
    hospital_treatment_ids = TreatmentPackage.objects.filter(
        hospital=hospital
    ).values_list('treatment_id', flat=True)

    # Get inquiries for these treatments
    hospital_inquiries = Inquiry.objects.filter(treatment_id__in=hospital_treatment_ids)
    total_inquiries = hospital_inquiries.count()

    # Pending approvals (status = 'NEW')
    pending_approvals = hospital_inquiries.filter(status='NEW').count()

    # Recent inquiries (last 5)
    recent_inquiries = hospital_inquiries.order_by('-created_at')[:5]

    # Upcoming appointments (assuming Appointment links to Inquiry)
    upcoming_appointments = Appointment.objects.filter(
        inquiry__in=hospital_inquiries,
        appointment_date__gte=datetime.today().date()  # only future appointments
    ).count()

    context = {
        "total_inquiries": total_inquiries,
        "pending_approvals": pending_approvals,
        "recent_inquiries": recent_inquiries,
        "upcoming_appointments": upcoming_appointments,
        "doctors": doctors,
        "packages": packages,
    }

    return render(request, "hospital_dashboard.html", context)

@hospital_required
def add_doctor(request):
    if request.method == "POST":
        form = DoctorForm(request.POST)
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
