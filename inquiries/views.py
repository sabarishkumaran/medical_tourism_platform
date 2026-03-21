from django.shortcuts import render, redirect

from inquiries.models import MedicalDocument
from .forms import InquiryForm


from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

@login_required
def submit_inquiry(request):
    if request.user.role != 'PATIENT':
        return HttpResponse("Unauthorized", status=403)


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


from django.core.paginator import Paginator

@login_required
def inquiry_hub(request):
    if request.user.role not in ['ADMIN', 'COORDINATOR'] and not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)

    from .models import ContactMessage
    from django.contrib import messages

    if request.method == "POST":
        message_id = request.POST.get('message_id')
        try:
            msg = ContactMessage.objects.get(id=message_id)
            # Toggle the is_read status
            msg.is_read = not msg.is_read
            msg.save()
            status_text = "Read" if msg.is_read else "Unread"
            messages.success(request, f"Message marked as {status_text}.")
        except ContactMessage.DoesNotExist:
            messages.error(request, "Message not found.")
        
        return redirect('inquiry_hub')

    messages_all = ContactMessage.objects.all().order_by('-created_at')
    
    paginator = Paginator(messages_all, 10) # 10 messages per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "inquiry_hub.html", {"page_obj": page_obj})
