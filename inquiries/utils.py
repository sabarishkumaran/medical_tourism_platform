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
