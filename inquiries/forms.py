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

        from django.utils import timezone
        
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500"
            })
            
        self.fields['travel_date'].widget.attrs.update({
            "min": timezone.now().date().isoformat()
        })

        if 'hospital' in self.fields:
            self.fields['hospital'].required = True

    def clean_travel_date(self):
        travel_date = self.cleaned_data.get('travel_date')
        if travel_date:
            from django.utils import timezone
            if travel_date < timezone.now().date():
                raise forms.ValidationError("Travel date cannot be in the past.")
        return travel_date

    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None:
            if budget <= 0 or budget > 1000000:
                raise forms.ValidationError("Budget must be between 1 and 1,000,000.")
        return budget

    def clean_documents(self):
        files = self.cleaned_data.get('documents')
        if not files:
            return files
        
        import os
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.pdf']
        
        # files can be a single file or list of files
        files_list = files if isinstance(files, list) else [files]
        
        for file in files_list:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    f"Only PNG, JPG, JPEG, and PDF files are allowed. '{file.name}' is invalid."
                )
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError(f"File '{file.name}' exceeds the 10MB size limit.")
                
        return files

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

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None:
            if price <= 0 or price > 1000000:
                raise forms.ValidationError("Price must be between 1 and 1,000,000.")
        return price

class ConfirmedInquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ["travel_date", "description"]
        widgets = {
            "travel_date": forms.DateInput(attrs={"type": "date"})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from django.utils import timezone
        
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 transition-all focus:bg-white focus:border-sky-500 focus:ring-4 focus:ring-sky-500/10 outline-none font-medium"
            })
            
        self.fields['travel_date'].widget.attrs.update({
            "min": timezone.now().date().isoformat()
        })

    def clean_travel_date(self):
        travel_date = self.cleaned_data.get('travel_date')
        if travel_date:
            from django.utils import timezone
            if travel_date < timezone.now().date():
                raise forms.ValidationError("Travel date cannot be in the past.")
        return travel_date