from .models import InquiryAuditLog

def log_inquiry_event(inquiry, user, action, notes=""):
    """
    Creates an audit log entry for an inquiry.
    
    Args:
        inquiry (Inquiry): The inquiry being logged.
        user (User): The user performing the action (can be None for system actions).
        action (str): A short description of the action (e.g. 'Created Inquiry', 'Status Changed').
        notes (str): Optional longer notes or details.
    """
    InquiryAuditLog.objects.create(
        inquiry=inquiry,
        user=user,
        action=action,
        notes=notes
    )

def send_payment_receipt(inquiry, amount, payment_choice):
    """Send a payment receipt email to the patient."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.template.loader import render_to_string
    
    try:
        html_message = render_to_string('generic_email_html.html', {
            'title': f"Payment Receipt - Inquiry #{inquiry.id}",
            'message': f"Dear {inquiry.patient.get_full_name() or inquiry.patient.username},\n\n"
                       f"We have successfully received your {payment_choice} payment of ${amount:.2f} "
                       f"for your treatment at {inquiry.hospital.name}.\n\n"
                       f"Thank you for choosing MedTour.",
        })
        
        send_mail(
            subject=f"Payment Receipt: Inquiry #{inquiry.id}",
            message=f"We have successfully received your {payment_choice} payment of ${amount:.2f}.",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[inquiry.patient.email],
            fail_silently=True,
            html_message=html_message
        )
    except Exception as e:
        print(f"Error sending receipt: {e}")

def send_commission_receipt(inquiry, amount):
    """Send a commission payment receipt email to the hospital."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.template.loader import render_to_string
    
    try:
        html_message = render_to_string('generic_email_html.html', {
            'title': f"Commission Payment Receipt - Inquiry #{inquiry.id}",
            'message': f"Dear Partner,\n\n"
                       f"We have successfully received your commission payment of ${amount:.2f} "
                       f"for Inquiry #{inquiry.id} (Patient: {inquiry.patient.get_full_name() or inquiry.patient.username}).\n\n"
                       f"Thank you for your prompt payment.",
        })
        
        send_mail(
            subject=f"Commission Payment Receipt: Inquiry #{inquiry.id}",
            message=f"We have successfully received your commission payment of ${amount:.2f}.",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[inquiry.hospital.user.email],
            fail_silently=True,
            html_message=html_message
        )
    except Exception as e:
        print(f"Error sending receipt: {e}")

def send_cumulative_commission_receipt(hospital, amount):
    """Send a cumulative commission payment receipt email to the hospital."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.template.loader import render_to_string
    
    try:
        html_message = render_to_string('generic_email_html.html', {
            'title': f"Bulk Commission Payment Receipt",
            'message': f"Dear Partner,\n\n"
                       f"We have successfully received your bulk commission payment of ${amount:.2f} "
                       f"for outstanding completed inquiries.\n\n"
                       f"Thank you for your prompt payment.",
        })
        
        send_mail(
            subject=f"Bulk Commission Payment Receipt",
            message=f"We have successfully received your bulk commission payment of ${amount:.2f}.",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[hospital.user.email],
            fail_silently=True,
            html_message=html_message
        )
    except Exception as e:
        print(f"Error sending receipt: {e}")

def send_subscription_update_email(hospital, plan_type, action):
    from django.core.mail import send_mail
    from django.conf import settings
    subject = f'Your MedTour Plan has been {action}'
    message = f'Hello {hospital.name},\n\nYour subscription plan has been {action.lower()} to {plan_type}.\n\nThank you,\nMedTour Team'
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [hospital.user.email])
    except Exception as e:
        pass
