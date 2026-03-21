from django.shortcuts import render, redirect
from .models import Treatment
from hospitals.models import Hospital


def home(request):

    treatments = Treatment.objects.all()[:6]
    hospitals = Hospital.objects.filter(status__iexact="APPROVED")[:6]
    countries = Hospital.objects.filter(status__iexact="APPROVED").exclude(user__country__isnull=True).exclude(user__country__exact="").values_list('user__country', flat=True).distinct()
    categories = Treatment.objects.values_list('category', flat=True).distinct()

    context = {
        "treatments": treatments,
        "hospitals": hospitals,
        "countries": countries,
        "categories": categories
    }

    return render(request, "home.html", context)

def treatment_list(request):
    from hospitals.models import TreatmentPackage
    packages = TreatmentPackage.objects.select_related('treatment', 'hospital').all()
    
    category = request.GET.get('category')
    country = request.GET.get('country')
    sort = request.GET.get('sort')

    if category:
        cat_lower = category.lower()
        if "ortho" in cat_lower:
            packages = packages.filter(treatment__category__icontains="Ortho")
        elif "dent" in cat_lower:
            packages = packages.filter(treatment__category__icontains="Dent")
        elif "cardio" in cat_lower:
            packages = packages.filter(treatment__category__icontains="Cardio")
        else:
            packages = packages.filter(treatment__category__icontains=category)
    if country and country != "All Countries":
        packages = packages.filter(hospital__user__country__icontains=country)
        
    from decimal import Decimal, InvalidOperation
    budget = request.GET.get('budget', '').strip()
    if budget:
        if "-" in budget:
            try:
                min_b, max_b = budget.split("-")
                packages = packages.filter(price__gte=Decimal(min_b), price__lte=Decimal(max_b))
            except (ValueError, InvalidOperation):
                pass
        elif "+" in budget:
            try:
                min_b = budget.replace('+', '').strip()
                packages = packages.filter(price__gte=Decimal(min_b))
            except (ValueError, InvalidOperation):
                pass



    if sort == "Price: Low to High":
        packages = packages.order_by('price')
    elif sort == "Price: High to Low" or sort == "Rating: High to Low":
        packages = packages.order_by('-price')

    countries = Hospital.objects.filter(status__iexact="APPROVED").exclude(user__country__isnull=True).exclude(user__country__exact="").values_list('user__country', flat=True).distinct()
    categories = Treatment.objects.values_list('category', flat=True).distinct()

    from django.core.paginator import Paginator
    paginator = Paginator(packages, 12) # 12 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "countries": countries,
        "categories": categories,
        "current_category": category,
        "current_country": country,
        "current_budget": budget,
        "current_sort": sort
    }
    return render(request, "treatments.html", context)

def concierge(request):
    return render(request, "concierge.html")

def blog(request):
    return render(request, "blog.html")

def about(request):
    return render(request, "about.html")

def contact(request):
    from inquiries.models import ContactMessage
    from django.contrib import messages
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        ContactMessage.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            message=message
        )
        messages.success(request, 'Message sent successfully! Our 24/7 team will get back to you shortly.')
        return redirect('contact')
    return render(request, "contact.html")
