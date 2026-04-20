from django.urls import path
from . import views
from .forms import CustomPasswordResetForm
from django.contrib.auth import views as auth_views

urlpatterns = [


    path('register/', views.register, name="register"),
    path('verify-email/', views.verify_otp, name="verify_otp"),
    path('resend-otp/', views.resend_otp, name="resend_otp"),
    path('request-reg-otp/', views.request_registration_otp, name="request_registration_otp"),
    path('verify-reg-otp/', views.verify_registration_otp, name="verify_registration_otp"),
    path('login/', views.user_login, name="login"),
    path('logout/', views.user_logout, name="logout"),
    path('profile/', views.profile_view, name='profile'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('dashboard/', views.patient_dashboard, name="patient_dashboard"),
    path('staff/manage/', views.manage_staff, name="manage_staff"),
    path('admin/dashboard/', views.admin_dashboard, name="admin_dashboard"),
    path('admin/patients/', views.admin_patients, name="admin_patients"),
    path('admin/patients/<int:user_id>/', views.patient_detail, name="patient_detail"),
    path('admin/revenue/commissions/', views.admin_revenue_commissions, name="admin_revenue_commissions"),
    path('admin/revenue/subscriptions/', views.admin_revenue_subscriptions, name="admin_revenue_subscriptions"),
    path('admin/revenue/leads/', views.admin_revenue_leads, name="admin_revenue_leads"),
    path('admin/revenue/services/', views.admin_revenue_services, name="admin_revenue_services"),
    path('admin/settings/subscriptions/', views.admin_subscription_settings, name="admin_subscription_settings"),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name="password_change.html"), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name="password_change_done.html"), name='password_change_done'),

    # Password Reset
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name="password_reset.html",
        email_template_name="password_reset_email.html",
        html_email_template_name="password_reset_email_html.html",
        subject_template_name="password_reset_subject.txt",
        form_class=CustomPasswordResetForm
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name="password_reset_done.html"), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="password_reset_confirm.html"), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"), name='password_reset_complete'),

]