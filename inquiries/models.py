from django.db import models
from accounts.models import User
from treatments.models import Treatment
from hospitals.models import Hospital




class Inquiry(models.Model):

    STATUS_CHOICES = [
        ("NEW", "New"),
        ("QUOTE_SENT", "Quote Sent"),
        ("CONFIRMED", "Confirmed"),
        ("PAYMENT_LINK_SENT", "Payment Link Sent"),
        ("COMPLETED", "Completed"),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE)

    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE)

    description = models.TextField()

    budget = models.IntegerField(null=True, blank=True)

    preferred_country = models.CharField(max_length=100, blank=True)

    travel_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="NEW"
    )

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True)
    package = models.ForeignKey('hospitals.TreatmentPackage', on_delete=models.SET_NULL, null=True, blank=True)

    service_fees_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    needs_visa_assistance = models.BooleanField(default=False)
    needs_travel_booking = models.BooleanField(default=False)
    needs_concierge = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inquiry {self.id}"
        
    @property
    def total_amount_paid(self):
        base_price = 0
        # A custom quote always overrides the initial package price
        latest_quote = self.quote_set.order_by('-created_at').first()
        if latest_quote:
            base_price = latest_quote.price
        elif self.package:
            base_price = self.package.price
        else:
            base_price = self.budget or 0
                
        return float(base_price) + float(self.service_fees_total)
    

class MedicalDocument(models.Model):

    inquiry = models.ForeignKey(
        Inquiry,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    file = models.FileField(upload_to="medical_reports/")

    uploaded_at = models.DateTimeField(auto_now_add=True)


class Quote(models.Model):

    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE)

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    treatment_plan = models.TextField()

    price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quote for Inquiry {self.inquiry.id}"

class ContactMessage(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.first_name} {self.last_name}"