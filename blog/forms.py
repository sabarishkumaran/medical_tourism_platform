from django import forms
from .models import BlogPost

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'category', 'image', 'excerpt', 'content']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full border border-slate-200 bg-slate-50 text-slate-800 rounded-xl shadow-sm px-4 py-3 focus:outline-none focus:bg-white focus:ring-2 focus:border-transparent focus:ring-sky-500 placeholder:text-slate-400 transition-colors"
            })
        self.fields['excerpt'].widget.attrs.update({"rows": "3", "placeholder": "Write a short 1-2 sentence hook for the preview card..."})
        self.fields['content'].widget.attrs.update({"rows": "15", "placeholder": "Write the full beautiful article here..."})
        self.fields['title'].widget.attrs.update({"placeholder": "Catchy Title Goes Here"})
