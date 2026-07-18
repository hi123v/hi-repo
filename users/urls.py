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
    path('teacher-login/', views.teacher_login, name='teacher-login'),
    path('teachers/', views.teachers, name='teachers'),
    path('teachers/add-student/', views.add_student, name='add-student'),
    path('teachers/add-class/', views.add_class, name='add-class'),
    path('invite/accept/<uuid:token>/', views.accept_invite, name='accept-invite'),
    path('invites/poll/', views.poll_invites, name='poll-invites'),
    path('invites/status/<uuid:token>/', views.invite_status, name='invite-status'),
    path('invites/decline/<uuid:token>/', views.decline_invite, name='decline-invite'),
    path('teachers/student/<str:username>/', views.teacher_student_detail, name='teacher-student-detail'),
    path('teachers/student/<str:username>/action/', views.teacher_action, name='teacher-student-action'),
    path('parents/', views.parents, name='parents'),
    path('placement-quiz/', views.placement_quiz, name='placement-quiz'),
    path('membership/', views.membership, name='membership'),
    path('class-management/', views.class_management, name='class-management'),
    # class dashboard and subpages
    path('teachers/class/<int:course_id>/', views.class_dashboard, name='class-dashboard'),
    path('teachers/class/<int:course_id>/students/', views.class_students, name='class-students'),
    path('teachers/class/<int:course_id>/analytics/', views.class_analytics, name='class-analytics'),
    path('teachers/class/<int:course_id>/profile/', views.class_profile_page, name='class-profile'),
    path('teachers/class/<int:course_id>/points/', views.class_points_page, name='class-points'),
    path('teachers/class/<int:course_id>/tasks/', views.class_task_manager, name='class-tasks'),
    path('teachers/class/<int:course_id>/lesson-planner/', views.class_lesson_planner, name='class-lesson-planner'),
    path('teachers/class/<int:course_id>/lesson/<int:lesson_id>/', views.class_lesson_detail, name='class-lesson-detail'),
    path('teachers/class/<int:course_id>/calendar/', views.class_calendar, name='class-calendar'),
    path('teachers/class/<int:course_id>/parents/', views.class_parents, name='class-parents'),
    path('teachers/class/<int:course_id>/toggle/', views.toggle_teacher_class, name='toggle-class'),
]