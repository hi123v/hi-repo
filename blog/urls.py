from django.urls import path
from .views import (
    number_pop_game,
    home,
    games,
    PostListView, 
    PostDetailView, 
    PostCreateView,
    PostUpdateView,
    PostDeleteView,
    UserPostListView,
    task_detail,
    complete_task,
)
from . import views

urlpatterns = [
    path('', home, name='home'),  # Home page   
    path('chat/', PostListView.as_view(), name='chat'),  
    path('user/<str:username>', UserPostListView.as_view(), name='user-posts'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/update/', PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post-delete'),
    path('task/<int:task_id>/', task_detail, name='task-detail'),  
    path('about/', views.about, name='blog-about'),
    path('games/', games, name='games'),
    path('games/number-pop/', number_pop_game, name='number-pop-game'),
    path('newsletter-signup/', views.newsletter_signup, name='newsletter-signup'),
    path('course/<int:course_id>/', views.course_detail, name='course-detail'),
    path('task/<int:task_id>/complete/', views.complete_task, name='complete-task'),
    path('task/<int:task_id>/uncomplete/', views.uncomplete_task, name='uncomplete-task'),
]