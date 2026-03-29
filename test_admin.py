import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medtour.settings')
django.setup()

from django.test import RequestFactory
from accounts.views import admin_dashboard
from accounts.models import User

req = RequestFactory().get('/admin/dashboard/')
req.user = User.objects.filter(role__in=['ADMIN', 'COORDINATOR']).first()
if req.user:
    resp = admin_dashboard(req)
    print("STATUS", resp.status_code)
else:
    print("NO ADMIN USER")
