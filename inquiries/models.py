from django.db import models
from accounts.models import User
from treatments.models import Treatment
from hospitals.models import Hospital
import uuid




class Inquiry(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    STATUS_CHOICES = [
        ("NEW", "New"),
        ("QUOTE_SENT", "Quote Sent"),
        ("CONFIRMED", "Confirmed"),
        ("PAYMENT_LINK_SENT", "Payment Link Sent"),
        ("AWAITING_NEXT_SITTING", "Awaiting Next Sitting"),
        ("COMPLETED", "Completed"),
        ("CANCELLED_REFUNDED", "Cancelled & Refunded"),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE)

    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE)

    description = models.TextField()

    budget = models.IntegerField(null=True, blank=True)

    preferred_country = models.CharField(max_length=100, blank=True)

    travel_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=30,
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

    treatment_completed = models.BooleanField(default=False)
    current_sitting_number = models.IntegerField(default=1)
    
    # New fields for payment, ticket, and commission flows
    booking_confirmed = models.BooleanField(default=False)
    payment_status = models.CharField(
        max_length=10,
        choices=[('UNPAID', 'Unpaid'), ('PARTIAL', 'Partially Paid'), ('FULL', 'Fully Paid')],
        default='UNPAID'
    )
    ticket_file = models.FileField(upload_to='travel_tickets/', null=True, blank=True)
    ticket_uploaded_at = models.DateTimeField(null=True, blank=True)
    commission_paid = models.BooleanField(default=False)
    commission_payment_link_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inquiry {self.id}"
        
    @property
    def total_amount_paid(self):
        # Calculate from actual recorded completed payments
        payments_sum = self.payment_set.filter(status__iexact='Completed').aggregate(models.Sum('amount'))['amount__sum'] or 0.00
        return float(payments_sum)


class InquiryAuditLog(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.inquiry.id} - {self.action} by {self.user.username if self.user else 'System'}"


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

class QuoteSitting(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='sittings')
    sitting_number = models.IntegerField()
    description = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Sitting {self.sitting_number} for Quote {self.quote.id}"

class ContactMessage(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    
    reply_text = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.first_name} {self.last_name}"


class InquiryMessage(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} on Inquiry #{self.inquiry.id}"