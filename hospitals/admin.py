from django.contrib import admin
from .models import Hospital, Doctor, Accreditation

admin.site.register(Hospital)
admin.site.register(Doctor)
admin.site.register(Accreditation)

# @admin.register(Hospital)
# class HospitalAdmin(admin.ModelAdmin):

#     list_display = ['name', 'country', 'city', 'status', 'created_at']

#     list_filter = ['status', 'country']

#     search_fields = ['name']