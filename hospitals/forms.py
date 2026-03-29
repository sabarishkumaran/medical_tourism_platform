# hospitals/forms.py
from django import forms
from .models import Doctor, Treatment, TreatmentPackage

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialization', 'experience_years', 'success_rate', 'bio', 'photo']

class TreatmentPackageForm(forms.ModelForm):
    treatment_name = forms.CharField(max_length=200, label="Treatment Name")
    category = forms.CharField(max_length=200, label="Category")
    description = forms.CharField(widget=forms.Textarea, label="Description")

    class Meta:
        model = TreatmentPackage
        fields = ['price', 'currency', 'stay_days', 'recovery_days', 'doctor']

    def __init__(self, *args, **kwargs):
        self.hospital = kwargs.pop('hospital')
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = Doctor.objects.filter(hospital=self.hospital)
        
        # Style all fields
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 transition-all focus:bg-white focus:border-sky-500 focus:ring-4 focus:ring-sky-500/10 outline-none'
            })

    def save(self, commit=True):
        name = self.cleaned_data['treatment_name']
        cat = self.cleaned_data['category']
        desc = self.cleaned_data['description']

        treatment, _ = Treatment.objects.get_or_create(
            name=name,
            defaults={'category': cat, 'description': desc}
        )

        package = super().save(commit=False)
        package.hospital = self.hospital
        package.treatment = treatment
        if commit:
            package.save()
        return package