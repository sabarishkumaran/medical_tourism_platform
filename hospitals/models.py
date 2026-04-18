from django.db import models
from django.db.models import Avg
from accounts.models import User
from treatments.models import Treatment



class Hospital(models.Model):

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
    )

    ACCREDITATION_CHOICES = (
        ('', 'Not Set'),
        ('JCI', 'JCI (Joint Commission International)'),
        ('NABH', 'NABH (National Accreditation Board)'),
        ('ISO', 'ISO 9001 Certified'),
        ('JACHO', 'JACHO Accredited'),
        ('OTHER', 'Other'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)

    city = models.CharField(max_length=100)

    description = models.TextField()

    accreditation = models.CharField(max_length=200, blank=True, choices=ACCREDITATION_CHOICES, default='')

    certificate = models.FileField(upload_to='hospital_certificates/', blank=True, null=True)

    established_year = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    suspension_reason = models.TextField(blank=True, default='')

    SUBSCRIPTION_PLAN_CHOICES = (
        ('BASIC', 'Basic (Free)'),
        ('PREMIUM', 'Premium ($199/mo)'),
        ('ELITE', 'Elite ($499/mo)'),
    )
    
    subscription_plan = models.CharField(max_length=20, choices=SUBSCRIPTION_PLAN_CHOICES, default='BASIC')
    subscription_end_date = models.DateField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_featured = models.BooleanField(default=False)

    beds_count = models.IntegerField(default=100)
    international_patients = models.IntegerField(default=1000)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def years_active(self):
        from datetime import date
        return date.today().year - self.established_year

    @property
    def average_rating(self):
        avg = self.review_set.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0.0

    def __str__(self):
        return self.name
    
class Doctor(models.Model):

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    name = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200)
    experience_years = models.IntegerField()

    success_rate = models.FloatField()

    bio = models.TextField(blank=True, default='')
    photo = models.ImageField(upload_to='doctor_photos/', null=True, blank=True)

    def __str__(self):
        return self.name
    
class TreatmentPackage(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    stay_days = models.IntegerField()
    recovery_days = models.IntegerField()
    def __str__(self):
        return f"{self.treatment.name} - {self.hospital.name}"

class HospitalImage(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hospital_images/')


class ReapprovalRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('REVIEWED', 'Reviewed'),
    )
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='reapproval_requests')
    comment = models.TextField()
    document = models.FileField(upload_to='reapproval_docs/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Reapproval: {self.hospital.name} ({self.submitted_at.strftime('%Y-%m-%d')})"
