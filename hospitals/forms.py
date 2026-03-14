# hospitals/forms.py
from django import forms
from .models import Doctor, Treatment, TreatmentPackage

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialization', 'experience_years', 'success_rate', 'bio']

class TreatmentPackageForm(forms.ModelForm):
    treatment_name = forms.CharField(max_length=200)
    treatment_category = forms.CharField(max_length=200)
    treatment_description = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = TreatmentPackage
        fields = ['price', 'currency', 'stay_days', 'recovery_days', 'doctor']

    def __init__(self, *args, **kwargs):
        self.hospital = kwargs.pop('hospital')  # pass the hospital
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        # Create Treatment if it doesn't exist
        name = self.cleaned_data['treatment_name']
        category = self.cleaned_data['treatment_category']
        description = self.cleaned_data['treatment_description']

        doctor = forms.ModelChoiceField(
            queryset=Doctor.objects.none(),  # Will set dynamically
            required=False,
            empty_label="No Doctor Available",
            widget=forms.Select(attrs={"class": "w-full border rounded p-2"})
        )

        treatment, created = Treatment.objects.get_or_create(
            name=name,
            defaults={'category': category, 'description': description}
        )

        package = super().save(commit=False)
        package.hospital = self.hospital
        package.treatment = treatment

        if commit:
            package.save()
        return package