from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def hospital_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/accounts/login/?next={request.path}')
        if request.user.role == 'HOSPITAL':
            hospital = request.user.hospital
            allowed_views = ['hospital_dashboard', 'notify_admin_aged_approval', 'submit_reapproval']
            if hospital.status != 'APPROVED' and view_func.__name__ not in allowed_views:
                return redirect('hospital_dashboard')
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper