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
    path('submit-patient-review/<uuid:inquiry_id>/', views.submit_patient_review, name="submit_patient_review"),
    path('upload-ticket/<uuid:inquiry_id>/', views.upload_ticket, name="upload_ticket"),
    path('send-commission-link/<uuid:inquiry_id>/', views.send_commission_link, name="send_commission_link"),
    path('pay-commission/<uuid:inquiry_id>/', views.pay_commission, name="pay_commission"),
    path('pay-commission/<uuid:inquiry_id>/create-order/', views.create_commission_order, name="create_commission_order"),
    path('pay-commission/<uuid:inquiry_id>/capture-order/', views.capture_commission_order, name="capture_commission_order"),
    path('cancel-refund/<uuid:inquiry_id>/', views.cancel_and_refund_inquiry, name="cancel_and_refund_inquiry"),
    path('book-next-sitting/<uuid:inquiry_id>/', views.book_next_sitting, name="book_next_sitting"),
    path('inquiry/<uuid:inquiry_id>/payment/create-order/', views.create_payment_order, name='create_payment_order'),
    path('inquiry/<uuid:inquiry_id>/payment/capture-order/', views.capture_payment_order, name='capture_payment_order'),
    path('inquiry/<uuid:inquiry_id>/payment/return/', views.payment_return, name='payment_return'),
    path('pay-commission/<uuid:inquiry_id>/return/', views.commission_return, name='commission_return'),
    path('record-offline-payment/<uuid:inquiry_id>/', views.record_offline_payment, name='record_offline_payment'),
    
    # Cumulative Commission Routes
    path('send-cumulative-link/<int:hospital_id>/', views.send_cumulative_commission_link, name="send_cumulative_commission_link"),
    path('pay-cumulative/<int:hospital_id>/', views.pay_cumulative_commission, name="pay_cumulative_commission"),
    path('pay-cumulative/<int:hospital_id>/create-order/', views.create_cumulative_order, name="create_cumulative_order"),
    path('pay-cumulative/<int:hospital_id>/capture-order/', views.capture_cumulative_order, name="capture_cumulative_order"),
    path('pay-cumulative/<int:hospital_id>/return/', views.cumulative_return, name="cumulative_return"),
]
