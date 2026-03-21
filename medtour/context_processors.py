from hospitals.models import Hospital
from inquiries.models import ContactMessage

def pending_hospitals_alerts(request):
    """
    Context processor to fetch the count of pending hospitals.
    Only queries the database if the user is an authenticated superuser.
    """
    count = 0
    unread_contacts_count = 0
    if request.user.is_authenticated and request.user.is_superuser:
        count = Hospital.objects.filter(status__iexact='PENDING').count()
        unread_contacts_count = ContactMessage.objects.filter(is_read=False).count()
    
    return {
        'pending_hospitals_count': count,
        'unread_contacts_count': unread_contacts_count
    }
