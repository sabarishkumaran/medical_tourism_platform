from django.db import models
from django.db.models import Avg
from accounts.models import User
from treatments.models import Treatment

class SubscriptionPlanConfig(models.Model):
    PLAN_CHOICES = [
        ('BASIC', 'Basic (Free)'),
        ('PREMIUM', 'Premium'),
        ('ELITE', 'Elite Executive'),
    ]
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_packages = models.IntegerField(default=5, help_text="-1 means unlimited")
    commission_free_leads = models.IntegerField(default=0)
    ranking_bonus = models.IntegerField(default=0)

    display_title = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.get_plan_type_display()} - ${self.price}/mo"
class Accreditation(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name} ({self.code})"

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

    @classmethod
    def get_accreditation_choices(cls):
        try:
            db_choices = [(a.code, f"{a.name} ({a.code})") for a in Accreditation.objects.all()]
            if db_choices:
                return [('', 'Not Set')] + db_choices
        except Exception:
            pass
        return cls.ACCREDITATION_CHOICES

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
    paypal_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    last_admin_notification_date = models.DateTimeField(null=True, blank=True)

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
    sittings_required = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
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

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('DEPOSIT', 'Deposit'),
        ('COMMISSION_FEE', 'Commission Fee'),
        ('SUBSCRIPTION', 'Subscription Fee'),
        ('TREATMENT_PAYMENT', 'Treatment Payment')
    )
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2) # positive or negative
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255)
    paypal_order_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type}: ${self.amount} ({self.hospital.name})"
