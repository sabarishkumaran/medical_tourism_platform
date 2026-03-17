from django.shortcuts import render
from .models import Treatment
from hospitals.models import Hospital


def home(request):

    treatments = Treatment.objects.all()[:6]
    hospitals = Hospital.objects.filter(status__iexact="APPROVED")[:6]

    context = {
        "treatments": treatments,
        "hospitals": hospitals
    }

    return render(request, "home.html", context)

def treatment_list(request):

    treatments = Treatment.objects.all()

    context = {
        "treatments": treatments
    }
    return render(request, "treatments.html", context)

def concierge(request):
    return render(request, "concierge.html")

def blog(request):
    return render(request, "blog.html")

def about(request):
    return render(request, "about.html")

def contact(request):
    return render(request, "contact.html")