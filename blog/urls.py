from django.urls import path
from .views import (
    home,
    PostListView, 
    PostDetailView, 
    PostCreateView,
    PostUpdateView,
    PostDeleteView,
    UserPostListView,
    TaskDetailView
)
from . import views

urlpatterns = [
    path('', home, name='home'),  # Home page   
    path('chat/', PostListView.as_view(), name='chat'),  # Chat page
    path('user/<str:username>', UserPostListView.as_view(), name='user-posts'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/update/', PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post-delete'),
    path('task/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('about/', views.about, name='blog-about'),
]