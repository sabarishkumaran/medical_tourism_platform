import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medtour.settings')
django.setup()

from treatments.models import Treatment

mapping = {
    "dental implantation": "Dental Implantation",
    "teeth whiting": "Teeth Whitening",
    "mutrology": "Neurology" # Assuming mutrology was a typo for Neurology
}

treatments = Treatment.objects.all()
for treatment in treatments:
    original_name = treatment.name
    
    # Check manual mapping first
    lower_name = original_name.lower().strip()
    if lower_name in mapping:
        treatment.name = mapping[lower_name]
    else:
        # Just title case it if it's not in the mapping
        treatment.name = original_name.title()
        
    if original_name != treatment.name:
        treatment.save()
        print(f"Updated '{original_name}' -> '{treatment.name}'")

print("Finished standardizing treatments.")
