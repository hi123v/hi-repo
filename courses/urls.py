from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='home'),
    path('courses/', views.course_list, name='course_list'),
    path('lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('blog/', views.blog, name='blog'),
]