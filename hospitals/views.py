from datetime import datetime

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.core.exceptions import PermissionDenied

from accounts.decorators import hospital_required
from appointments.models import Appointment
from hospitals.forms import DoctorForm, TreatmentPackageForm
from inquiries.models import Inquiry
from .models import Hospital, Doctor, TreatmentPackage, HospitalImage, ReapprovalRequest
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
    elif status_filter == 'REINSTATEMENT':
        hospitals_all = Hospital.objects.filter(status='SUSPENDED', reapproval_requests__status='PENDING').distinct().order_by('-user__date_joined')
    elif status_filter == 'SUSPENDED':
        hospitals_all = Hospital.objects.filter(status='SUSPENDED').exclude(reapproval_requests__status='PENDING').distinct().order_by('-user__date_joined')
    else:
        hospitals_all = Hospital.objects.filter(status=status_filter).order_by('-user__date_joined')
        
    from django.core.paginator import Paginator
    
    paginator = Paginator(hospitals_all, 10)
    page_number = request.GET.get('page')
    hospitals = paginator.get_page(page_number)
    
    for hosp in hospitals:
        hosp.has_reinstatement = hosp.reapproval_requests.filter(status='PENDING').exists()
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/pending_hospital_grid.html", {"hospitals": hospitals, "status_filter": status_filter})
        
    return render(request, "pending_hospitals.html", {"hospitals": hospitals, "status_filter": status_filter})

@hospital_required
def upload_hospital_photos(request):
    hospital = request.user.hospital
    if request.method == "POST":
        images = request.FILES.getlist('photos')
        valid_images = []
        errors = []
        from django.core.files.images import get_image_dimensions
        
        for img in images:
            try:
                w, h = get_image_dimensions(img)
                if w and h:
                    if w < 200 or h < 200:
                        errors.append(f"{img.name}: Resolution too low (min 200x200).")
                        continue
                    ratio = w / h
                    if ratio < 0.3 or ratio > 3.0:
                        errors.append(f"{img.name}: Aspect ratio too extreme.")
                        continue
                valid_images.append(img)
            except Exception:
                errors.append(f"{img.name}: Invalid image file.")
                
        for img in valid_images:
            HospitalImage.objects.create(hospital=hospital, image=img)
            
        if valid_images:
            messages.success(request, f'Successfully uploaded {len(valid_images)} photos.')
        if errors:
            for error in errors:
                messages.error(request, error)
        return redirect('hospital_dashboard')
    
    return render(request, "upload_hospital_photos.html", {"hospital": hospital})

@login_required
def review_hospital(request, hospital_id):

    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Unauthorized access.")

    hospital = get_object_or_404(Hospital, id=hospital_id)
    reapproval_requests = hospital.reapproval_requests.all()
    has_pending_request = reapproval_requests.filter(status='PENDING').exists()

    return render(request, "review_hospital.html", {
        "hospital": hospital,
        "accreditation_choices": Hospital.ACCREDITATION_CHOICES,
        "reapproval_requests": reapproval_requests,
        "has_pending_request": has_pending_request,
    })

@login_required
def approve_hospital(request, hospital_id):

    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Unauthorized access.")

    if request.method != "POST":
        return redirect("review_hospital", hospital_id=hospital_id)

    hospital = get_object_or_404(Hospital, id=hospital_id)
    previous_status = hospital.status

    if previous_status in ['REJECTED', 'SUSPENDED']:
        has_pending = hospital.reapproval_requests.filter(status='PENDING').exists()
        if not has_pending:
            messages.error(request, "This hospital must submit a reapproval request before it can be approved.")
            return redirect("review_hospital", hospital_id=hospital_id)

    accreditation = request.POST.get("accreditation", "")
    hospital.accreditation = accreditation
    hospital.status = "APPROVED"
    hospital.save()
    
    # Mark all pending reapproval requests as REVIEWED
    hospital.reapproval_requests.filter(status='PENDING').update(status='REVIEWED')

    from django.template.loader import render_to_string
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse
    
    is_reinstatement = previous_status in ('SUSPENDED', 'REJECTED')
    login_link = request.build_absolute_uri(reverse('login'))
    html_message = render_to_string('hospital_approved_email_html.html', {
        'hospital': hospital,
        'login_link': login_link,
        'is_reinstatement': is_reinstatement,
    })
    
    email_subject = "MedTour Account Reinstated!" if is_reinstatement else "MedTour Application Approved!"
    email_body = f"Your account for {hospital.name} has been successfully reinstated." if is_reinstatement else f"Congratulations! Your application for {hospital.name} has been approved."
    
    send_mail(
        email_subject,
        email_body,
        settings.DEFAULT_FROM_EMAIL,
        [hospital.user.email],
        html_message=html_message,
        fail_silently=True
    )

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
    from django.http import JsonResponse

    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Unauthorized access.")

    if request.method != "POST":
        return redirect("review_hospital", hospital_id=hospital_id)

    password = request.POST.get('password', '')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept', '') == 'application/json'

    if not request.user.check_password(password):
        if is_ajax: return JsonResponse({'success': False, 'error': 'Invalid administrator password.'})
        messages.error(request, 'Invalid password. Action aborted.')
        return redirect('review_hospital', hospital_id=hospital_id)

    hospital = get_object_or_404(Hospital, id=hospital_id)
    reason = request.POST.get('suspension_reason', '').strip()

    if len(reason) < 250:
        if is_ajax: return JsonResponse({'success': False, 'error': 'Reason must be at least 250 characters.'})
        messages.error(request, 'Reason must be at least 250 characters.')
        return redirect('review_hospital', hospital_id=hospital_id)

    hospital.status = "REJECTED"
    hospital.suspension_reason = reason
    hospital.save()

    from django.template.loader import render_to_string
    from django.core.mail import send_mail
    from django.conf import settings
    
    html_message = render_to_string('hospital_rejected_email_html.html', {
        'hospital': hospital,
        'reason': reason,
    })
    send_mail(
        "MedTour Application Update",
        f"Your application for {hospital.name} has been rejected.",
        settings.DEFAULT_FROM_EMAIL,
        [hospital.user.email],
        html_message=html_message,
        fail_silently=True
    )

    messages.success(request, f'{hospital.name} has been rejected.')

    if is_ajax:
        return JsonResponse({'success': True})

    if request.headers.get('HX-Request'):
        from django.core.paginator import Paginator
        hospitals_all = Hospital.objects.filter(status='PENDING').order_by('-user__date_joined')
        paginator = Paginator(hospitals_all, 10)
        page_number = request.GET.get('page', 1)
        hospitals = paginator.get_page(page_number)
        return render(request, "partials/pending_hospital_grid.html", {"hospitals": hospitals})

    return redirect("pending_hospitals")


@login_required
def suspend_hospital(request, hospital_id):
    from django.http import JsonResponse

    if not (request.user.role in ['ADMIN', 'COORDINATOR'] or request.user.is_superuser):
        raise PermissionDenied("Administrative access required.")

    if request.method != "POST":
        return redirect("review_hospital", hospital_id=hospital_id)

    password = request.POST.get('password', '')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept', '') == 'application/json'

    if not request.user.check_password(password):
        if is_ajax: return JsonResponse({'success': False, 'error': 'Invalid administrator password.'})
        messages.error(request, 'Invalid password. Action aborted.')
        return redirect('review_hospital', hospital_id=hospital_id)

    hospital = get_object_or_404(Hospital, id=hospital_id)
    reason = request.POST.get('suspension_reason', '').strip()
    
    if len(reason) < 250:
        if is_ajax: return JsonResponse({'success': False, 'error': 'Suspension reason must be at least 250 characters.'})
        messages.error(request, 'Suspension reason must be at least 250 characters.')
        return redirect('review_hospital', hospital_id=hospital_id)

    hospital.status = 'SUSPENDED'
    hospital.suspension_reason = reason
    hospital.save()
    
    # Mark existing requests as REVIEWED on new suspension
    hospital.reapproval_requests.filter(status='PENDING').update(status='REVIEWED')

    from django.template.loader import render_to_string
    from django.core.mail import send_mail
    from django.conf import settings
    
    html_message = render_to_string('hospital_suspended_email_html.html', {
        'hospital': hospital,
        'reason': reason,
    })
    send_mail(
        "MedTour Account Status Update",
        f"Your account for {hospital.name} has been suspended.",
        settings.DEFAULT_FROM_EMAIL,
        [hospital.user.email],
        html_message=html_message,
        fail_silently=True
    )

    messages.success(request, f'{hospital.name} has been suspended.')
    
    if is_ajax:
        return JsonResponse({'success': True})
        
    return redirect('review_hospital', hospital_id=hospital_id)


@hospital_required
def submit_reapproval(request):
    hospital = request.user.hospital
    if hospital.status not in ('SUSPENDED', 'REJECTED'):
        return redirect('hospital_dashboard')

    if request.method == 'POST':
        comment = request.POST.get('comment', '').strip()
        document = request.FILES.get('document')
        if comment:
            ReapprovalRequest.objects.create(
                hospital=hospital,
                comment=comment,
                document=document,
            )
            
            # Send Notification to Admins and Coordinators
            from django.db.models import Q
            from django.core.mail import send_mail
            from accounts.models import User
            from django.conf import settings
            from django.urls import reverse
            from django.template.loader import render_to_string
            
            admin_emails = list(User.objects.filter(
                (Q(role__in=['ADMIN', 'COORDINATOR']) | Q(is_superuser=True)) & Q(is_active=True)
            ).values_list('email', flat=True).distinct())
            if admin_emails:
                admin_subject = f"Reapproval Request Submitted by {hospital.name}"
                review_link = request.build_absolute_uri(reverse('pending_hospitals'))
                html_message = render_to_string('admin_hospital_signup_email_html.html', {
                    'hospital': hospital,
                    'review_link': review_link,
                    'is_reapproval': True,
                })
                send_mail(
                    admin_subject, 
                    f"The hospital {hospital.name} has addressed its suspension items and requested reinstation.", 
                    settings.DEFAULT_FROM_EMAIL, 
                    admin_emails, 
                    html_message=html_message, 
                    fail_silently=True
                )
            
            messages.success(request, 'Your reapproval request has been submitted. Our team will review it shortly.')
        else:
            messages.error(request, 'Please provide a comment explaining the changes you have made.')
    return redirect('hospital_dashboard')


@login_required
def notify_admin_aged_approval(request):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
        
    if request.user.role != 'HOSPITAL':
        raise PermissionDenied
        
    hospital = request.user.hospital
    if hospital.status != 'PENDING':
        from django.contrib import messages
        messages.error(request, "You do not have a pending application.")
        return redirect('hospital_dashboard')
        
    from django.utils import timezone
    from datetime import timedelta
    
    is_aged = hospital.user.date_joined < (timezone.now() - timedelta(days=3))
    can_notify = True
    if hospital.last_admin_notification_date:
        can_notify = hospital.last_admin_notification_date < (timezone.now() - timedelta(days=1))
        
    if not is_aged:
        from django.contrib import messages
        messages.error(request, "Your application was submitted recently. Please wait for the initial review period.")
        return redirect('hospital_dashboard')
        
    if not can_notify:
        from django.contrib import messages
        messages.error(request, "You have already notified the admin today. Please wait for their response.")
        return redirect('hospital_dashboard')
        
    # Send Notification
    from django.db.models import Q
    from django.core.mail import send_mail
    from accounts.models import User
    from django.conf import settings
    from django.urls import reverse
    from django.template.loader import render_to_string
    
    admin_emails = list(User.objects.filter(
        (Q(role__in=['ADMIN', 'COORDINATOR']) | Q(is_superuser=True)) & Q(is_active=True)
    ).values_list('email', flat=True).distinct())
    if admin_emails:
        admin_subject = f"Urgent: Aged Approval Escalation for {hospital.name}"
        review_link = request.build_absolute_uri(reverse('pending_hospitals'))
        html_message = render_to_string('admin_hospital_signup_email_html.html', {
            'hospital': hospital,
            'review_link': review_link,
            'is_escalation': True,
        })
        send_mail(
            admin_subject, 
            f"The hospital {hospital.name} has escalated their application as it has been pending for more than 3 days.", 
            settings.DEFAULT_FROM_EMAIL, 
            admin_emails, 
            html_message=html_message, 
            fail_silently=True
        )
        
    hospital.last_admin_notification_date = timezone.now()
    hospital.save(update_fields=['last_admin_notification_date'])
    
    from django.contrib import messages
    messages.success(request, "Administrators have been notified of your pending application.")
    return redirect('hospital_dashboard')

@hospital_required
def hospital_dashboard(request):
    hospital_user = request.user
    hospital = hospital_user.hospital

    if hospital.status != 'APPROVED':
        reapproval_requests = hospital.reapproval_requests.all()
        has_pending_request = reapproval_requests.filter(status='PENDING').exists()
        
        from django.utils import timezone
        from datetime import timedelta
        is_aged = hospital.user.date_joined < (timezone.now() - timedelta(days=3))
        can_notify = True
        if hospital.last_admin_notification_date:
            can_notify = hospital.last_admin_notification_date < (timezone.now() - timedelta(days=1))
            
        return render(request, "hospital_pending_approval.html", {
            "hospital": hospital,
            "reapproval_requests": reapproval_requests,
            "has_pending_request": has_pending_request,
            "is_aged": is_aged,
            "can_notify": can_notify,
        })
    doctors = Doctor.objects.filter(hospital=hospital)
    packages = TreatmentPackage.objects.filter(hospital=hospital).order_by('-id')[:3]

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

    # Recent inquiries (last 5)
    recent_inquiries = hospital_inquiries.order_by('-created_at')[:5]

    # Upcoming appointments (assuming Appointment links to Inquiry)
    upcoming_appointments = Appointment.objects.filter(
        inquiry__in=hospital_inquiries,
        appointment_date__gte=datetime.today().date()  # only future appointments
    ).count()

    # Calculate Estimated Revenue
    confirmed_inquiries = hospital_inquiries.filter(status__in=['CONFIRMED', 'PAYMENT_LINK_SENT', 'COMPLETED'])
    revenue_sum = 0
    for inq in confirmed_inquiries:
        quote = inq.quote_set.order_by('-created_at').first()
        if quote:
            revenue_sum += float(quote.price)
        elif inq.package:
            revenue_sum += float(inq.package.price)
        else:
            revenue_sum += float(inq.budget or 0)
    
    if revenue_sum >= 1000:
        estimated_revenue = f"${revenue_sum / 1000:.1f}k"
    else:
        estimated_revenue = f"${revenue_sum:.0f}"

    from django.utils import timezone
    current_date = timezone.now().date()

    context = {
        "total_inquiries": total_inquiries,
        "pending_approvals": pending_approvals,
        "pending_quotes": pending_quotes,
        "recent_inquiries": recent_inquiries,
        "upcoming_appointments": upcoming_appointments,
        "estimated_revenue": estimated_revenue,
        "doctors": doctors,
        "packages": packages,
        "current_date": current_date,
    }

    return render(request, "hospital_dashboard.html", context)

@hospital_required
def manage_doctors(request):
    hospital = request.user.hospital
    from django.core.paginator import Paginator
    from django.db.models import Avg
    doctors_all = Doctor.objects.filter(hospital=hospital).order_by('name')
    
    total_staff = doctors_all.count()
    specialties_count = doctors_all.values('specialization').distinct().count()
    avg_success_rate = doctors_all.aggregate(avg=Avg('success_rate'))['avg'] or 0
    
    paginator = Paginator(doctors_all, 12)
    page_number = request.GET.get('page')
    doctors = paginator.get_page(page_number)
    
    return render(request, "manage_doctors.html", {
        "hospital": hospital,
        "doctors": doctors,
        "total_staff": total_staff,
        "specialties_count": specialties_count,
        "avg_success_rate": round(avg_success_rate, 1),
        "avg_rating": hospital.average_rating
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
    hospital = request.user.hospital
    
    # Enforce dynamic package limits
    current_count = TreatmentPackage.objects.filter(hospital=hospital).count()
    from hospitals.models import SubscriptionPlanConfig
    plan_config = SubscriptionPlanConfig.objects.filter(plan_type=hospital.subscription_plan).first()
    
    if plan_config and plan_config.max_packages != -1 and current_count >= plan_config.max_packages:
        from django.contrib import messages
        messages.error(request, f"Your {plan_config.display_title} plan allows up to {plan_config.max_packages} packages. Please upgrade to add more.")
        return redirect('hospital_billing')

    if request.method == "POST":
        form = TreatmentPackageForm(request.POST, hospital=hospital)
        if form.is_valid():
            form.save()
            return redirect('hospital_dashboard')
    else:
        form = TreatmentPackageForm(hospital=hospital)
    return render(request, "add_treatment_package.html", {"form": form})

@hospital_required
def edit_treatment_package(request, package_id):
    package = get_object_or_404(TreatmentPackage, id=package_id)
    if package.hospital != request.user.hospital:
        raise PermissionDenied("Unauthorized access.")
        
    if request.method == "POST":
        form = TreatmentPackageForm(request.POST, request.FILES, instance=package, hospital=request.user.hospital)
        if form.is_valid():
            form.save()
            return redirect('hospital_dashboard')
    else:
        form = TreatmentPackageForm(instance=package, hospital=request.user.hospital)
        
    return render(request, "edit_treatment_package.html", {"form": form, "package": package})

@hospital_required
def manage_treatment_packages(request):
    hospital = request.user.hospital
    packages = TreatmentPackage.objects.filter(hospital=hospital).order_by('-id')
    return render(request, "manage_treatment_packages.html", {
        "hospital": hospital,
        "packages": packages
    })

@hospital_required
def delete_treatment_package(request, package_id):
    package = get_object_or_404(TreatmentPackage, id=package_id)
    if package.hospital != request.user.hospital:
        raise PermissionDenied("Unauthorized access.")
        
    if request.method == "POST":
        package.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse("")
        return redirect('hospital_dashboard')
    raise PermissionDenied()

@hospital_required
def toggle_package_active(request, package_id):
    package = get_object_or_404(TreatmentPackage, id=package_id)
    if package.hospital != request.user.hospital:
        raise PermissionDenied("Unauthorized access.")
        
    if request.method == "POST":
        package.is_active = not package.is_active
        package.save()
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('hospital_dashboard')
    raise PermissionDenied()

@hospital_required
def edit_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if doctor.hospital != request.user.hospital:
        raise PermissionDenied("Unauthorized access.")
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
        raise PermissionDenied("Unauthorized access.")
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
            raise PermissionDenied("Unauthorized access.")
        package.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse("")  # HTMX will remove the target
    return redirect('hospital_dashboard')

@hospital_required
def manage_treatment_packages(request):
    hospital = request.user.hospital
    from django.core.paginator import Paginator
    packages_all = TreatmentPackage.objects.filter(hospital=hospital).order_by('treatment__name')
    
    total_packages = packages_all.count()
    active_packages = total_packages  # All packages are considered active for now
    
    paginator = Paginator(packages_all, 12)
    page_number = request.GET.get('page')
    packages = paginator.get_page(page_number)
    
    return render(request, "manage_treatment_packages.html", {
        "hospital": hospital,
        "packages": packages,
        "total_packages": total_packages,
        "active_packages": active_packages,
    })

@hospital_required
def manage_inquiries(request):
    hospital = request.user.hospital
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    hospital_treatment_ids = TreatmentPackage.objects.filter(
        hospital=hospital
    ).values_list('treatment_id', flat=True)

    inquiries_all = Inquiry.objects.filter(
        Q(hospital=hospital) | Q(treatment_id__in=hospital_treatment_ids)
    ).distinct().order_by('-created_at')
    
    status_filter = request.GET.get('status', 'all')
    
    if status_filter == 'new':
        inquiries_all = inquiries_all.filter(status='NEW')
    elif status_filter == 'quotes':
        inquiries_all = inquiries_all.filter(status='QUOTE_SENT')
        
    paginator = Paginator(inquiries_all, 15)
    page_number = request.GET.get('page')
    inquiries = paginator.get_page(page_number)
    
    from django.utils import timezone
    current_date = timezone.now().date()
    
    return render(request, "manage_inquiries.html", {
        "hospital": hospital,
        "inquiries": inquiries,
        "current_status": status_filter,
        "current_date": current_date,
    })

@hospital_required
def hospital_billing(request):
    hospital = request.user.hospital
    transactions = hospital.transactions.all().order_by('-created_at')[:50]
    
    from hospitals.models import SubscriptionPlanConfig
    plans = SubscriptionPlanConfig.objects.all().order_by('price')
    plan_data = { p.plan_type: p for p in plans }
    
    # Proration Data
    from datetime import date
    remaining_days = 0
    if hospital.subscription_end_date and hospital.subscription_end_date > date.today():
        remaining_days = (hospital.subscription_end_date - date.today()).days
    
    current_plan_config = plan_data.get(hospital.subscription_plan)
    current_plan_price = current_plan_config.price if current_plan_config else 0
    
    return render(request, "hospital_billing.html", {
        "hospital": hospital,
        "transactions": transactions,
        "plan_data": plan_data,
        "remaining_days": remaining_days,
        "current_plan_price": current_plan_price,
    })



@hospital_required
def toggle_auto_renew(request):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
        
    hospital = request.user.hospital
    hospital.auto_renew = not hospital.auto_renew
    hospital.save()
    
    return HttpResponse("")
    
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
            Q(user__country__name__icontains=query)
        )
    
    if country:
        hospitals_all = hospitals_all.filter(user__country__name__icontains=country)
        
    if accreditation:
        hospitals_all = hospitals_all.filter(accreditation__iexact=accreditation)
        
    paginator = Paginator(hospitals_all, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get distinct countries for filter dropdown
    countries = Hospital.objects.filter(status='APPROVED').exclude(user__country__isnull=True).values_list('user__country__name', flat=True).distinct()
    
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
