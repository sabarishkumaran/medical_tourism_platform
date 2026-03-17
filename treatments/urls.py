from django.urls import path
from . import views

urlpatterns = [

    path('', views.home, name="home"),
    path('treatments/', views.treatment_list, name="treatments"),
    path('concierge/', views.concierge, name="concierge"),
    path('blog/', views.blog, name="blog"),
    path('about/', views.about, name="about"),
    path('contact/', views.contact, name="contact"),
]