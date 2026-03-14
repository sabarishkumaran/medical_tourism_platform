from django.urls import path
from . import views

urlpatterns = [

    path('', views.home, name="home"),
    path('treatments/', views.treatment_list, name="treatments"),

]