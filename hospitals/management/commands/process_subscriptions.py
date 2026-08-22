from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from hospitals.models import Hospital, SubscriptionPlanConfig, Transaction
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Processes expired hospital subscriptions (downgrades them if not renewed via PayPal).'

    def handle(self, *args, **options):
        today = date.today()
        # Find approved hospitals whose subscription period has ended
        expired_hospitals = Hospital.objects.filter(
            status='APPROVED',
            subscription_end_date__lt=today
        ).exclude(subscription_plan='BASIC')

        self.stdout.write(f"Found {expired_hospitals.count()} expired subscriptions to process.")

        for hospital in expired_hospitals:
            self.stdout.write(self.style.WARNING(f"Subscription expired for {hospital.name}. Downgrading."))
            old_plan = hospital.get_subscription_plan_display()
            hospital.subscription_plan = 'BASIC'
            hospital.subscription_end_date = None
            hospital.paypal_subscription_id = None
            hospital.save()

            self.send_subscription_email(hospital, success=False, reason="Subscription period ended and was not renewed", old_plan=old_plan)

    def send_subscription_email(self, hospital, success, **kwargs):
        subject = "MedTour Subscription Update"
        if success:
            subject = f"Your {kwargs.get('plan_name')} Subscription Renewed!"
            template = 'subscription_renewal_email_html.html'
            context = {
                'hospital': hospital,
                'success': True,
                'plan_name': kwargs.get('plan_name'),
                'price': kwargs.get('price'),
                'next_billing': hospital.subscription_end_date,
                'login_link': f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}"
            }
        else:
            subject = "MedTour Subscription Downgraded"
            template = 'subscription_renewal_email_html.html'
            context = {
                'hospital': hospital,
                'success': False,
                'reason': kwargs.get('reason'),
                'old_plan': kwargs.get('old_plan'),
                'login_link': f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}"
            }

        html_message = render_to_string(template, context)
        send_mail(
            subject,
            "",
            settings.DEFAULT_FROM_EMAIL,
            [hospital.user.email],
            html_message=html_message,
            fail_silently=True
        )
