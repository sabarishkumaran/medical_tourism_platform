from django.urls import path
from . import views

urlpatterns = [

    path('submit/', views.submit_inquiry, name="submit_inquiry"),
    path('submit/load-treatments/', views.load_hospital_treatments, name="load_hospital_treatments"),
    path('get-price/', views.get_treatment_price, name="get_treatment_price"),
    path('hub/', views.inquiry_hub, name="inquiry_hub"),
    path('contact-messages/', views.contact_messages_hub, name="contact_messages_hub"),
    path('respond/<uuid:inquiry_id>/', views.respond_inquiry, name="respond_inquiry"),
    path('view/<uuid:inquiry_id>/', views.inquiry_detail, name="view_inquiry"),
    path('my-inquiries/', views.patient_inquiries, name="patient_inquiries"),
    path('accept/<uuid:inquiry_id>/', views.accept_quote, name="accept_quote"),
    path('edit-confirmation/<uuid:inquiry_id>/', views.edit_confirmation, name="edit_confirmation"),
    path('send-payment/<uuid:inquiry_id>/', views.send_payment_link, name="send_payment_link"),
    path('pay/<uuid:inquiry_id>/', views.process_payment, name="process_payment"),
    path('mark-completed/<uuid:inquiry_id>/', views.mark_treatment_completed, name="mark_treatment_completed"),
    path('submit-review/<uuid:inquiry_id>/', views.submit_review, name="submit_review"),
    path('cancel-refund/<uuid:inquiry_id>/', views.cancel_and_refund_inquiry, name="cancel_and_refund_inquiry"),
    path('book-next-sitting/<uuid:inquiry_id>/', views.book_next_sitting, name="book_next_sitting"),
]
