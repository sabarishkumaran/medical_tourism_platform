from django.shortcuts import render, redirect

from inquiries.models import MedicalDocument
from .forms import InquiryForm


def submit_inquiry(request):

    if request.method == "POST":

        form = InquiryForm(request.POST ,request.FILES)

        if form.is_valid():

            inquiry = form.save(commit=False)
            inquiry.patient = request.user
            inquiry.save()

            files = request.FILES.getlist("documents")

            for file in files:

                MedicalDocument.objects.create(
                    inquiry=inquiry,
                    file=file
                )

            return redirect("patient_dashboard")

    else:

        form = InquiryForm()

    return render(request, "submit_inquiry.html", {"form": form})