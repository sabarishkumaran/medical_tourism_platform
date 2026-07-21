from django.db import models
from hospitals.models import Hospital
from accounts.models import User


class Review(models.Model):

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    patient = models.ForeignKey(User, on_delete=models.CASCADE)

    rating = models.IntegerField()

    comment = models.TextField()
    
    inquiry = models.OneToOneField('inquiries.Inquiry', on_delete=models.CASCADE, null=True, blank=True, related_name='review')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.rating}"


class PatientReview(models.Model):
    inquiry = models.OneToOneField('inquiries.Inquiry', on_delete=models.CASCADE, related_name='patient_review')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PatientReview {self.rating} for {self.patient.username}"