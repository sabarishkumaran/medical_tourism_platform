from django.urls import path
from . import views

urlpatterns = [

    path('submit/', views.submit_inquiry, name="submit_inquiry"),

]