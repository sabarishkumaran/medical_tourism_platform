from django.core.exceptions import PermissionDenied

def hospital_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'HOSPITAL':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper