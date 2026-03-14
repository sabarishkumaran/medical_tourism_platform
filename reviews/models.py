from django.db import models
from hospitals.models import Hospital
from accounts.models import User


class Review(models.Model):

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    patient = models.ForeignKey(User, on_delete=models.CASCADE)

    rating = models.IntegerField()

    comment = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.rating}"