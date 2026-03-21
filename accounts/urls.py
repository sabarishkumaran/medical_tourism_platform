from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [


    path('register/', views.register, name="register"),
    path('login/', views.user_login, name="login"),
    path('logout/', views.user_logout, name="logout"),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.patient_dashboard, name="patient_dashboard"),
    path('staff/manage/', views.manage_staff, name="manage_staff"),
    path('admin/dashboard/', views.admin_dashboard, name="admin_dashboard"),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name="password_change.html"), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name="password_change_done.html"), name='password_change_done'),

]