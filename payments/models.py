from django.db import models
from inquiries.models import Inquiry


class Payment(models.Model):

    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    currency = models.CharField(max_length=10, default="USD")

    status = models.CharField(max_length=50)

    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id}"