import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medtour.settings')
django.setup()

from inquiries.models import Inquiry

inquiries = Inquiry.objects.all()
for inquiry in inquiries:
    inquiry.uuid = uuid.uuid4()
    inquiry.save()
print(f"Updated {inquiries.count()} inquiries.")
