from django.urls import path
from . import views

urlpatterns = [

    path('pending/', views.pending_hospitals, name="pending_hospitals"),

    path('approve/<int:hospital_id>/', views.approve_hospital, name="approve_hospital"),

    path('reject/<int:hospital_id>/', views.reject_hospital, name="reject_hospital"),

    path('<int:id>/', views.hospital_detail, name="hospital_detail"),

    path('dashboard/', views.hospital_dashboard, name='hospital_dashboard'),

    path('doctors/add/', views.add_doctor, name='add_doctor'),

    path('treatment-packages/add/', views.add_treatment_package, name='add_treatment_package'),



]