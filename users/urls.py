from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import CustomLoginView

urlpatterns = [
    path('register/', views.register, name='register'),
    path('register/<str:role>/', views.register, name='register-role'),
    path('register/switch/<str:role>/', views.re_register, name='re-register'),
    path('profile/', views.profile, name='profile'),  # <-- use lowercase 'profile'
    path('user/<str:username>/', views.user_profile, name='user-profile'),
    path('friend-request/send/<str:username>/', views.send_friend_request, name='send-friend-request'),
    path('friend-request/accept/<int:request_id>/', views.accept_friend_request, name='accept-friend-request'),
    path('streak-request/send/<str:username>/', views.send_streak_request, name='send-streak-request'),
    path('streak-request/accept/<int:request_id>/', views.accept_streak_request, name='accept-streak-request'),
    path('follow/<str:username>/', views.toggle_follow, name='toggle-follow'),
    path('following/', views.following_list, name='following-list'),
    path('choose-login/', views.choose_login, name='choose-login'),
    path('login/', CustomLoginView.as_view(template_name='users/login_form.html'), name='login'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('student-login/', views.student_login, name='student-login'),
    path('teachers/', views.teachers, name='teachers'),
    path('parents/', views.parents, name='parents'),
    path('placement-quiz/', views.placement_quiz, name='placement-quiz'),
    path('membership/', views.membership, name='membership'),
    path('class-management/', views.class_management, name='class-management'),
]