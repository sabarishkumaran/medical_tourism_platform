from django.shortcuts import render, redirect
from .models import Treatment
from hospitals.models import Hospital
from reviews.models import Review

def home(request):

    treatments = Treatment.objects.all()[:6]
    
    from django.db.models import Case, When, Value, IntegerField
    hospitals = Hospital.objects.filter(status__iexact="APPROVED").annotate(
        plan_rank=Case(
            When(subscription_plan='ELITE', then=Value(3)),
            When(subscription_plan='PREMIUM', then=Value(2)),
            When(subscription_plan='BASIC', then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).order_by('-plan_rank', 'user__date_joined')[:6]
    
    countries = Hospital.objects.filter(status__iexact="APPROVED").exclude(user__country__isnull=True).values_list('user__country__name', flat=True).distinct()
    categories = Treatment.objects.values_list('category', flat=True).distinct()
    
    # Fetch top patient reviews for "Patient Stories"
    reviews = Review.objects.filter(rating__gte=4).order_by('-created_at')[:10]

    # Calculate Budget Range for the slider
    from hospitals.models import TreatmentPackage
    from django.db.models import Min, Max
    price_stats = TreatmentPackage.objects.filter(hospital__status='APPROVED', is_active=True).aggregate(
        min_p=Min('price'), 
        max_p=Max('price')
    )
    min_possible = price_stats.get('min_p')
    max_possible = price_stats.get('max_p')

    context = {
        "treatments": treatments,
        "hospitals": hospitals,
        "countries": countries,
        "categories": categories,
        "reviews": reviews,
        "min_possible_price": int(min_possible or 1000),
        "max_possible_price": int(max_possible or 50000),
        "avg_possible_price": (int(min_possible or 1000) + int(max_possible or 50000)) // 2
    }

    return render(request, "home.html", context)

def treatment_list(request):
    from hospitals.models import TreatmentPackage
    packages = TreatmentPackage.objects.select_related('treatment', 'hospital').filter(
        hospital__status='APPROVED',
        is_active=True
    )

    
    category = request.GET.get('category')
    country = request.GET.get('country')
    accreditation = request.GET.get('accreditation')
    sort = request.GET.get('sort')
    query = request.GET.get('q', '').strip()

    if query:
        from django.db.models import Q
        packages = packages.filter(
            Q(treatment__name__icontains=query) | 
            Q(hospital__name__icontains=query) |
            Q(treatment__category__icontains=query)
        )

    if accreditation:
        packages = packages.filter(hospital__accreditation__iexact=accreditation)

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
        packages = packages.filter(hospital__user__country__name__icontains=country)
        
    from decimal import Decimal, InvalidOperation
    budget = request.GET.get('budget', '').strip()
    min_budget = request.GET.get('min_budget', '').strip()
    max_budget = request.GET.get('max_budget', '').strip()

    if min_budget and max_budget:
        try:
            packages = packages.filter(price__gte=Decimal(min_budget), price__lte=Decimal(max_budget))
        except (ValueError, InvalidOperation):
            pass
    elif budget:
        if budget.isdigit():
            try:
                max_price = Decimal(budget)
                packages = packages.filter(price__lte=max_price)
            except (ValueError, InvalidOperation):
                pass
        elif "-" in budget:
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



    from django.db.models import Case, When, Value, IntegerField
    # Default order places higher-tiered plans first
    packages = packages.annotate(
        plan_rank=Case(
            When(hospital__subscription_plan='ELITE', then=Value(3)),
            When(hospital__subscription_plan='PREMIUM', then=Value(2)),
            When(hospital__subscription_plan='BASIC', then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    )

    if sort == "Price: Low to High":
        packages = packages.order_by('price', '-plan_rank')
    elif sort == "Price: High to Low" or sort == "Rating: High to Low":
        packages = packages.order_by('-price', '-plan_rank')
    else:
        packages = packages.order_by('-plan_rank')

    countries = Hospital.objects.filter(status__iexact="APPROVED").exclude(user__country__isnull=True).values_list('user__country__name', flat=True).distinct()
    categories = Treatment.objects.values_list('category', flat=True).distinct()

    from django.core.paginator import Paginator
    paginator = Paginator(packages, 12) # 12 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    from django.db.models import Min, Max
    price_stats = TreatmentPackage.objects.filter(hospital__status='APPROVED', is_active=True).aggregate(
        min_p=Min('price'), 
        max_p=Max('price')
    )
    min_possible = price_stats.get('min_p')
    max_possible = price_stats.get('max_p')

    context = {
        "page_obj": page_obj,
        "countries": countries,
        "categories": categories,
        "current_category": category,
        "current_country": country,
        "current_budget": budget,
        "current_min_budget": min_budget or str(int(min_possible or 1000)),
        "current_max_budget": max_budget or str(int(max_possible or 50000)),
        "current_accreditation": accreditation,
        "current_sort": sort,
        "query": query,
        "accreditation_options": Hospital.ACCREDITATION_CHOICES,
        "min_possible_price": int(min_possible or 1000),
        "max_possible_price": int(max_possible or 50000)
    }
    
    if request.headers.get('HX-Request'):
        return render(request, "partials/package_list.html", context)
        
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
        
        if request.headers.get('HX-Request'):
            return render(request, "partials/contact_success.html")
            
        messages.success(request, 'Message sent successfully! Our 24/7 team will get back to you shortly.')
        return redirect('contact')
    return render(request, "contact.html")
