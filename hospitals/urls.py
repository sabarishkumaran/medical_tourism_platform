from django.urls import path
from . import views

urlpatterns = [

    path('pending/', views.pending_hospitals, name="pending_hospitals"),

    path('review/<int:hospital_id>/', views.review_hospital, name="review_hospital"),

    path('approve/<int:hospital_id>/', views.approve_hospital, name="approve_hospital"),

    path('reject/<int:hospital_id>/', views.reject_hospital, name="reject_hospital"),

    path('<int:id>/', views.hospital_detail, name="hospital_detail"),

    path('dashboard/', views.hospital_dashboard, name='hospital_dashboard'),
    path('doctors/', views.manage_doctors, name='manage_doctors'),
    path('photos/upload/', views.upload_hospital_photos, name='upload_hospital_photos'),

    path('doctors/add/', views.add_doctor, name='add_doctor'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    path('doctors/<int:doctor_id>/edit/', views.edit_doctor, name='edit_doctor'),
    path('doctors/<int:doctor_id>/delete/', views.delete_doctor, name='delete_doctor'),

    path('treatment-packages/add/', views.add_treatment_package, name='add_treatment_package'),
    path('treatment-packages/<int:package_id>/edit/', views.edit_treatment_package, name='edit_treatment_package'),
    path('treatment-packages/<int:package_id>/delete/', views.delete_treatment_package, name='delete_treatment_package'),
    path('suspend/<int:hospital_id>/', views.suspend_hospital, name='suspend_hospital'),
    path('reapproval/submit/', views.submit_reapproval, name='submit_reapproval'),
    path('list/', views.hospital_list, name="hospital_list"),

]