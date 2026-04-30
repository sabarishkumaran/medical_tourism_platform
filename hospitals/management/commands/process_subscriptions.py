from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from hospitals.models import Hospital, SubscriptionPlanConfig, WalletTransaction
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Processes automated hospital subscription renewals and wallet debits.'

    def handle(self, *args, **options):
        today = date.today()
        # Find approved hospitals whose subscription period has ended
        expired_hospitals = Hospital.objects.filter(
            status='APPROVED',
            subscription_end_date__lte=today
        ).exclude(subscription_plan='BASIC')

        self.stdout.write(f"Found {expired_hospitals.count()} hospitals to process.")

        for hospital in expired_hospitals:
            self.stdout.write(f"Processing {hospital.name} (Plan: {hospital.subscription_plan})")
            
            # Get plan config for price
            plan_config = SubscriptionPlanConfig.objects.filter(plan_type=hospital.subscription_plan).first()
            plan_price = plan_config.price if plan_config else Decimal('0.00')

            if hospital.auto_renew:
                if hospital.wallet_balance >= plan_price:
                    # SUCCESSFUL RENEWAL
                    hospital.wallet_balance -= plan_price
                    hospital.subscription_end_date = today + relativedelta(months=+1)
                    hospital.save()

                    # Record transaction
                    WalletTransaction.objects.create(
                        hospital=hospital,
                        amount=-plan_price,
                        transaction_type='SUBSCRIPTION',
                        description=f"Automated monthly renewal: {hospital.get_subscription_plan_display()}"
                    )

                    self.send_subscription_email(hospital, success=True, plan_name=hospital.get_subscription_plan_display(), price=plan_price)
                    self.stdout.write(self.style.SUCCESS(f"Successfully renewed {hospital.name}"))
                else:
                    # INSUFFICIENT FUNDS -> DOWNGRADE
                    self.stdout.write(self.style.WARNING(f"Insufficient funds for {hospital.name}. Downgrading."))
                    old_plan = hospital.get_subscription_plan_display()
                    hospital.subscription_plan = 'BASIC'
                    hospital.subscription_end_date = None
                    hospital.save()

                    self.send_subscription_email(hospital, success=False, reason="Insufficient wallet balance", old_plan=old_plan)
            else:
                # AUTO-RENEW DISABLED -> DOWNGRADE
                self.stdout.write(f"Auto-renew disabled for {hospital.name}. Downgrading.")
                old_plan = hospital.get_subscription_plan_display()
                hospital.subscription_plan = 'BASIC'
                hospital.subscription_end_date = None
                hospital.save()

                self.send_subscription_email(hospital, success=False, reason="Auto-renew is disabled", old_plan=old_plan)

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
