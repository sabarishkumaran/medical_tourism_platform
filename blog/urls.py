from django.urls import path
from . import views

urlpatterns = [
    path('', views.blog_list, name='blog_list'),
    path('write/', views.blog_write, name='blog_write'),
    path('my-articles/', views.my_articles, name='my_articles'),
    path('edit/<int:pk>/', views.author_blog_edit, name='author_blog_edit'),
    path('pending/', views.admin_pending_blogs, name='admin_pending_blogs'),
    path('approve/<int:pk>/', views.approve_blog, name='approve_blog'),
    path('pending/edit/<int:pk>/', views.admin_blog_edit, name='admin_blog_edit'),
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),
]
