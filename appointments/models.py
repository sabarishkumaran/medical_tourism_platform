from django.db import models
from inquiries.models import Inquiry
from hospitals.models import Hospital


class Appointment(models.Model):

    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE)

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    appointment_date = models.DateTimeField()

    hospital_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Appointment {self.id}" 