from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = (
        ('PATIENT', 'Patient'),
        ('HOSPITAL', 'Hospital'),
        ('ADMIN', 'Admin'),
        ('COORDINATOR', 'Coordinator'),
    )

    COUNTRY_CHOICES = (
        ('India', 'India'),
        ('Thailand', 'Thailand'),
        ('Turkey', 'Turkey'),
        ('Mexico', 'Mexico'),
        ('UAE', 'United Arab Emirates'),
        ('Singapore', 'Singapore'),
        ('Malaysia', 'Malaysia'),
        ('Spain', 'Spain'),
        ('Brazil', 'Brazil'),
        ('Germany', 'Germany'),
        ('USA', 'United States'),
        ('UK', 'United Kingdom'),
        ('Australia', 'Australia'),
        ('Canada', 'Canada'),
        ('France', 'France'),
        ('Jordan', 'Jordan'),
        ('Costa Rica', 'Costa Rica'),
        ('South Korea', 'South Korea'),
        ('South Africa', 'South Africa'),
        ('Poland', 'Poland'),
        ('Czech Republic', 'Czech Republic'),
        ('Hungary', 'Hungary'),
        ('Other', 'Other'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, choices=COUNTRY_CHOICES, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username
class OTPVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='otp_verification')
    otp_code = models.CharField(max_length=6)
    unverified_email = models.EmailField(blank=True, null=True, help_text="Used when changing email address")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OTP for {self.user.username}"


class PatientProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    medical_history = models.TextField(blank=True)

    def __str__(self):
        return self.user.username

import uuid

class StaffInvitation(models.Model):
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitation for {self.email} ({self.role})"