from .models import ContactMessage

def unread_contact_count(request):
    if request.user.is_authenticated and request.user.role in ['ADMIN', 'COORDINATOR']:
        try:
            count = ContactMessage.objects.filter(is_read=False).count()
            return {'unread_contact_count': count}
        except:
            return {'unread_contact_count': 0}
    return {'unread_contact_count': 0}
