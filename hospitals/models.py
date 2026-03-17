from django.db import models
from accounts.models import User
from treatments.models import Treatment



class Hospital(models.Model):

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Doctor(models.Model):

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    name = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200)
    experience_years = models.IntegerField()

    success_rate = models.FloatField()

    bio = models.TextField()

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