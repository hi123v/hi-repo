from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import CustomLoginView

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),  # <-- use lowercase 'profile'
    path('choose-login/', views.choose_login, name='choose-login'),
    path('login/', CustomLoginView.as_view(template_name='users/login_form.html'), name='login'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('student-login/', views.student_login, name='student-login'),
    path('placement-quiz/', views.placement_quiz, name='placement-quiz'),
    path('membership/', views.membership, name='membership'),
    path('class-management/', views.class_management, name='class-management'),
]