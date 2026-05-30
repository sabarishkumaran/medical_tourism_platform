# hospitals/forms.py
from django import forms
from .models import Doctor, Treatment, TreatmentPackage

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialization', 'experience_years', 'success_rate', 'bio', 'photo']

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            from django.core.files.images import get_image_dimensions
            try:
                w, h = get_image_dimensions(photo)
                if w and h:
                    if w < 200 or h < 200:
                        raise forms.ValidationError("Image resolution is too low. Minimum 200x200 pixels required.")
                    ratio = w / h
                    if ratio < 0.3 or ratio > 3.0:
                        raise forms.ValidationError("Image aspect ratio is too extreme. Please upload a more balanced image.")
            except Exception:
                pass
        return photo

class TreatmentPackageForm(forms.ModelForm):
    treatment_name = forms.CharField(max_length=200, label="Treatment Name")
    category = forms.CharField(max_length=200, label="Category")
    description = forms.CharField(widget=forms.Textarea, label="Description")

    class Meta:
        model = TreatmentPackage
        fields = ['price', 'currency', 'stay_days', 'recovery_days', 'sittings_required', 'doctor']

    def __init__(self, *args, **kwargs):
        self.hospital = kwargs.pop('hospital')
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = Doctor.objects.filter(hospital=self.hospital)
        
        # Pre-populate treatment-related fields if editing an existing package
        if self.instance and self.instance.pk and self.instance.treatment:
            self.fields['treatment_name'].initial = self.instance.treatment.name
            self.fields['category'].initial = self.instance.treatment.category
            self.fields['description'].initial = self.instance.treatment.description
        
        # Update price field to indicate it's a starting price
        self.fields['price'].label = "Starting Price"
        self.fields['price'].help_text = "This is the base price. Final price will be determined based on patient's medical condition during quote process."
        
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