from django import forms
from .models import User

from django.contrib.auth.forms import UserCreationForm, PasswordResetForm

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("There is no account registered with this email address.")
        return email
class RegisterForm(UserCreationForm):

    hospital_name = forms.CharField(required=False)
    hospital_city = forms.CharField(required=False)
    hospital_address = forms.CharField(required=False)
    hospital_description = forms.CharField(required=False, widget=forms.Textarea)
    hospital_established_year = forms.IntegerField(required=False)
    hospital_certificate = forms.FileField(required=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "role",
            "phone",
            "country",
            "password1",
            "password2"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict public registration to only Patient and Hospital roles
        self.fields['role'].choices = [
            ('PATIENT', 'Patient'),
            ('HOSPITAL', 'Hospital'),
        ]

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            })

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')

        if role == 'PATIENT':
            if not first_name:
                self.add_error('first_name', 'First name is required for patient accounts.')
            if not last_name:
                self.add_error('last_name', 'Last name is required for patient accounts.')

        if role == 'HOSPITAL':
            if not cleaned_data.get('hospital_name'):
                self.add_error('hospital_name', 'This field is required for hospitals.')
            if not cleaned_data.get('hospital_city'):
                self.add_error('hospital_city', 'This field is required for hospitals.')
            if not cleaned_data.get('hospital_address'):
                self.add_error('hospital_address', 'This field is required for hospitals.')
            if not cleaned_data.get('hospital_description'):
                self.add_error('hospital_description', 'This field is required for hospitals.')
            if not cleaned_data.get('hospital_established_year'):
                self.add_error('hospital_established_year', 'This field is required for hospitals.')
            if not self.files.get('hospital_certificate'):
                self.add_error('hospital_certificate', 'Certificate document is mandatory for hospitals.')
        return cleaned_data


class StaffCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit choices to staff roles
        self.fields['role'].choices = [
            ('ADMIN', 'Admin'),
            ('COORDINATOR', 'Coordinator'),
        ]
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:bg-white focus:border-sky-500 outline-none"
            })
    


class ProfileForm(forms.ModelForm):
    remove_avatar = forms.BooleanField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'country', 'avatar']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance.role == 'HOSPITAL':
            self.fields['first_name'].label = "Admin First Name"
            self.fields['last_name'].label = "Admin Last Name"
            self.fields['first_name'].required = False
            self.fields['last_name'].required = False


        # If the user is a hospital, show hospital-specific fields
        if hasattr(self.instance, 'hospital'):
            self.fields['hospital_name'] = forms.CharField(
                initial=self.instance.hospital.name, label="Hospital Name"
            )
            self.fields['hospital_address'] = forms.CharField(
                initial=self.instance.hospital.address, label="Address"
            )
            self.fields['hospital_city'] = forms.CharField(
                initial=self.instance.hospital.city, label="City"
            )
            self.fields['hospital_description'] = forms.CharField(
                initial=self.instance.hospital.description, label="Description", widget=forms.Textarea
            )

        # If the user is a patient, show patient-specific fields
        elif hasattr(self.instance, 'patientprofile'):
            self.fields['date_of_birth'] = forms.DateField(
                initial=self.instance.patientprofile.date_of_birth,
                required=False,
                widget=forms.DateInput(attrs={'type': 'date'})
            )
            self.fields['medical_history'] = forms.CharField(
                initial=self.instance.patientprofile.medical_history,
                required=False,
                widget=forms.Textarea
            )

    def save(self, commit=True):
        user = super().save(commit=commit)
        if self.cleaned_data.get('remove_avatar'):
            user.avatar = None
            if commit:
                user.save()
                
        if hasattr(user, 'hospital'):
            hospital = user.hospital
            hospital.name = self.cleaned_data.get('hospital_name')
            hospital.address = self.cleaned_data.get('hospital_address')
            hospital.city = self.cleaned_data.get('hospital_city')
            hospital.description = self.cleaned_data.get('hospital_description')
            hospital.save()
        elif hasattr(user, 'patientprofile'):
            profile = user.patientprofile
            profile.date_of_birth = self.cleaned_data.get('date_of_birth')
            profile.medical_history = self.cleaned_data.get('medical_history')
            profile.save()
        return user