from hospitals.models import Hospital
from inquiries.models import Inquiry
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import ProfileForm, RegisterForm
from .models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required

@login_required
def patient_dashboard(request):

    inquiries = Inquiry.objects.filter(patient=request.user)

    return render(request, "patient_dashboard.html", {
        "inquiries": inquiries
    })

def register(request):

    if request.method == "POST":

        form = RegisterForm(request.POST, request.FILES)

        if form.is_valid():

            user = form.save()

            # if role is hospital create hospital record
            if user.role == "HOSPITAL":

                Hospital.objects.create(
                    user=user,
                    name=form.cleaned_data["hospital_name"],
                    city=form.cleaned_data["hospital_city"],
                    address=form.cleaned_data["hospital_address"],
                    description=form.cleaned_data["hospital_description"],
                    established_year=form.cleaned_data["hospital_established_year"],
                    certificate=request.FILES.get("hospital_certificate"),
                )

            return redirect("login")

            # login(request, user)

            # return redirect("patient_dashboard")

    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})


def user_login(request):

    if request.method == "POST":

        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():

            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                if user.role == 'HOSPITAL':
                    return redirect("hospital_dashboard")
                elif user.role in ['ADMIN', 'COORDINATOR']:
                    return redirect("pending_hospitals")
                else:
                    return redirect("patient_dashboard")

    else:
        form = AuthenticationForm()

    return render(request, "login.html", {"form": form})

def user_logout(request):

    logout(request)

    return redirect("home")

@login_required
def profile_view(request):
    user = request.user

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile details updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=user)

    return render(request, "profile.html", {"form": form})