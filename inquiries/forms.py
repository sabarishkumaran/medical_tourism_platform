from django import forms
from .models import Inquiry

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class InquiryForm(forms.ModelForm):

    documents = forms.FileField(
        widget=MultipleFileInput(),

        required=False
    )

    class Meta:
        model = Inquiry
        fields = [
            "treatment",
            "description",
            "budget",
            "preferred_country",
            "travel_date"
        ]

        widgets = {
            "travel_date": forms.DateInput(attrs={"type": "date"})
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500"
            })