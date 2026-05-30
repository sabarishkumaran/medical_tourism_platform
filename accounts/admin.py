from django.contrib import admin
from .models import  PatientProfile, User, Country
admin.site.register(User)
admin.site.register(PatientProfile)
admin.site.register(Country)

