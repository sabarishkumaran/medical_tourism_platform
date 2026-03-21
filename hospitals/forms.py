# hospitals/forms.py
from django import forms
from .models import Doctor, Treatment, TreatmentPackage

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialization', 'experience_years', 'success_rate', 'bio', 'photo']

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
        # Filter doctor queryset to only those belonging to this hospital
        self.fields['doctor'].queryset = Doctor.objects.filter(hospital=self.hospital)

    def save(self, commit=True):
        # Create Treatment if it doesn't exist
        name = self.cleaned_data['treatment_name']
        category = self.cleaned_data['treatment_category']
        description = self.cleaned_data['treatment_description']

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