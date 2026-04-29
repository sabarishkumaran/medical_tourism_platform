from django.shortcuts import redirect
from django.conf import settings

class HospitalApprovalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated and request.user.role == 'HOSPITAL':
            hospital = getattr(request.user, 'hospital', None)
            if hospital and hospital.status != 'APPROVED':
                # Allow static and media
                if request.path.startswith(settings.STATIC_URL) or (settings.MEDIA_URL and request.path.startswith(settings.MEDIA_URL)):
                    return None
                
                allowed_views = [
                    'hospital_dashboard',
                    'notify_admin_aged_approval',
                    'submit_reapproval',
                    'logout',
                ]
                
                url_name = request.resolver_match.url_name if request.resolver_match else None
                if url_name not in allowed_views and not request.path.startswith('/admin/'):
                    return redirect('hospital_dashboard')
        return None
