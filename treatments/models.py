from django.db import models


class Treatment(models.Model):

    name = models.CharField(max_length=200)

    category = models.CharField(max_length=200)

    description = models.TextField()

    def __str__(self):
        return self.name
    

