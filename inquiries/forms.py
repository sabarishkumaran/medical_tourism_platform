from django import forms
from .models import Inquiry

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class InquiryForm(forms.ModelForm):

    documents = MultipleFileField(
        required=False
    )

    class Meta:
        model = Inquiry
        fields = [
            "treatment",
            "hospital",
            "package",
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

        if 'hospital' in self.fields:
            self.fields['hospital'].required = True

from .models import Quote

class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ['treatment_plan', 'price']
        widgets = {
            'treatment_plan': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the proposed treatment plan, duration, and facilities...'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 transition-all focus:bg-white focus:border-sky-500 focus:ring-4 focus:ring-sky-500/10 outline-none"
            })

class ConfirmedInquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ["travel_date", "description"]
        widgets = {
            "travel_date": forms.DateInput(attrs={"type": "date"})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 transition-all focus:bg-white focus:border-sky-500 focus:ring-4 focus:ring-sky-500/10 outline-none font-medium"
            })