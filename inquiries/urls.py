from django.urls import path
from . import views

urlpatterns = [

    path('submit/', views.submit_inquiry, name="submit_inquiry"),
    path('hub/', views.inquiry_hub, name="inquiry_hub"),

]
